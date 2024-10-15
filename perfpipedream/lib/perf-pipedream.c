#include <asm/unistd.h>
#include <limits.h>
#include <linux/perf_event.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <alloca.h>
#include <unistd.h>

#include "perf-pipedream.h"

#define EVENTSET_FREE ((void *)-1ull)

#ifdef __GNUC__
#define UNFREQUENT(exp) __builtin_expect((exp), 0)
#else
#define UNFREQUENT(exp) (exp)
#endif

#define VERBOSE(level, ...) (void)({			\
        if (UNFREQUENT(level)) {                        \
            fprintf(stderr, "DEBUG: perf_pipedream: "); \
            fprintf(stderr, __VA_ARGS__);               \
            fprintf(stderr, "\n");                      \
        }                                               \
	0;						\
    })

#define MAY_TRAP(trap, retcode) ({                                      \
            if (UNFREQUENT(trap) && retcode != PERFPIPEDREAM_SUCCESS) { \
                fprintf(stderr, "TRAP: perf_pipedream: unexpected error (%d): %s\n", retcode, perf_pipedream_strerror(retcode)); \
                abort();                                                \
            }                                                           \
            retcode;                                                    \
        })

#define SPRINT_LIST(buffer, buffer_size, n_elts, elts) sprint_int_list(buffer, buffer_size, n_elts, sizeof(*elts), (void *)elts)

static char *sprint_int_list(char *buffer, int buffer_size, int n_elts, int elt_size, void *elts) {
    int n = 0;
    const char *sep = "";
    buffer[0] = '\0';
    for (int e = 0; e < n_elts; e++) {
        int r;
        long long int value = 0;
        if (elt_size == sizeof(int))
            value = ((int *)elts)[e];
        else if (elt_size == sizeof(long int))
            value = ((long int *)elts)[e];
        else if (elt_size == sizeof(long long int))
            value = ((long long int *)elts)[e];
        r = snprintf(buffer + n, buffer_size - n, "%s%lld", sep, value);
        if (r >= buffer_size - n) break;
        n += r;
        sep = ", ";
    }
    return buffer;
}

const char *PERFPIPEDREAM_EVENTS_NAME[] = {
    "PERFPIPEDREAM_NO_EVENT",
    "PAPI_TOT_CYC",
    "PAPI_TOT_INS",
};

const int PERFPIPEDREAM_NUM_EVENTS = 3;

typedef struct {
    int fd;
} s_perf_event_config_t;

struct perf_event_attr **RUNNING_PE = NULL;
s_perf_event_config_t **RUNNING_PE_CONFIG = NULL;
int NUM_RUNNING_PE = 0;

// Array of array of events or `EVENTSET_FREE`
int **ALL_EVENT_SET = NULL;
// Number of events for each event set
int *NUM_PE = NULL;
// Total maximal number of event set
int NUM_EVENT_SET = 0;

int DEBUG = 0;
int TRAP = 0;
int IS_INIT = 0;
int RUNNING = 0;

static int event_idx_to_config(int idx, __u64 *config) {
    switch (idx) {
        // 0 is reserved as an end marker of the event list
    case 1: // PAPI_TOT_CYCLE
        *config = PERF_COUNT_HW_CPU_CYCLES;
        return PERFPIPEDREAM_SUCCESS;
    case 2: // PAPI_TOT_INS
        *config = PERF_COUNT_HW_INSTRUCTIONS;
        return PERFPIPEDREAM_SUCCESS;
    default:
        *config = 0;
        return PERFPIPEDREAM_ENO_EVENT_IDX;
    }
}

int perf_pipedream_query_event(int event_code) {
    if (event_code < PERFPIPEDREAM_NUM_EVENTS)
        return PERFPIPEDREAM_SUCCESS;
    else
        return PERFPIPEDREAM_ENO_EVENT_IDX;  // Do not trap, it can be used as a query
}

const char *perf_pipedream_strerror(int errcode) {
    switch (errcode) {
    case PERFPIPEDREAM_SUCCESS:
        return ("Operation completed successfully");
    case PERFPIPEDREAM_EEVENT_NOTFOUND:
        return ("Event name not found");
    case PERFPIPEDREAM_ENO_EVENT_IDX:
        return ("Event set has an unknown event");
    case PERFPIPEDREAM_EPERF_OPEN:
        return ("Error occured during perf_event_open syscall");
    case PERFPIPEDREAM_EEVENT_ALREADY_EXISTS:
        return ("Event already exist in event set");
    case PERFPIPEDREAM_EALREADY_RUNNING:
        return ("One event capture set is already running, more are unsupported");
    case PERFPIPEDREAM_ENOT_RUNNING:
        return ("Event capture is not running");
    case PERFPIPEDREAM_EEVENTSET_NOTFOUND:
        return ("Event set not found");
    case PERFPIPEDREAM_EEVENTSET_NONEMPTY:
        return ("Event set is not empty");
    case PERFPIPEDREAM_EEVENTSET_NOTNULL:
        return ("Event set is not PERFPIPEDREAM_NULL");
    case PERFPIPEDREAM_EALREADY_INIT:
        return ("Library already initialized");
    case PERFPIPEDREAM_EINVALID_VERSION:
        return ("Invalid version selected");
    case PERFPIPEDREAM_EEVENT_NOT_IN_SET:
        return ("Event is not present in event set");
    case PERFPIPEDREAM_EEVENT_SET_RUNNING:
        return ("Event set is currently running");
    case PERFPIPEDREAM_EEVENTSET_NULL:
        return ("Event set is not initialized");
    default:
        return ("Unknown error. Something *real bad* happened here");
    }
}

static long perf_event_open(struct perf_event_attr *hw_event, pid_t pid, int cpu,
                            int group_fd, unsigned long flags) {
    int ret;

    ret = syscall(__NR_perf_event_open, hw_event, pid, cpu, group_fd, flags);
    return ret;
}

int perf_pipedream_library_init(int version) {
    DEBUG = getenv("PERF_PIPEDREAM_DEBUG") != NULL;
    TRAP = getenv("PERF_PIPEDREAM_TRAP") != NULL;
    VERBOSE(DEBUG, "perf_pipedream_library_init(%d)", version);
    if (version != PERFPIPEDREAM_CURRENT_VERSION)
        return MAY_TRAP(TRAP, PERFPIPEDREAM_EINVALID_VERSION);

    if (IS_INIT == 1)
        return MAY_TRAP(TRAP, PERFPIPEDREAM_EALREADY_INIT);

    IS_INIT = 1;
    return PERFPIPEDREAM_CURRENT_VERSION;
}

void perf_pipedream_shutdown() {
    VERBOSE(DEBUG, "perf_pipedream_shutdown()");
    if (RUNNING) {
        perf_pipedream_stop(RUNNING, NULL);
    }
    for (int i = 0; i < NUM_EVENT_SET; ++i) {
        if (ALL_EVENT_SET[i] != EVENTSET_FREE) {
            free(ALL_EVENT_SET[i]);
            ALL_EVENT_SET[i] = EVENTSET_FREE;
        }
    }
    free(ALL_EVENT_SET);
    ALL_EVENT_SET = NULL;
    free(NUM_PE);
    NUM_PE = NULL;
    NUM_EVENT_SET = 0;
    IS_INIT = 0;
}

int perf_pipedream_is_initialized() {
    VERBOSE(DEBUG, "perf_pipedream_is_initialized()");
    return IS_INIT;
}

int perf_pipedream_event_name_to_code(const char *event_name, int *event_code) {
    VERBOSE(DEBUG, "perf_pipedream_event_name_to_code(%s, %p)", event_name, event_code);
    for (int i = 0; i < PERFPIPEDREAM_NUM_EVENTS; ++i) {
        if (!strcmp(event_name, PERFPIPEDREAM_EVENTS_NAME[i])) {
            *event_code = i;
            goto success;
        }
    }
    return PERFPIPEDREAM_EEVENT_NOTFOUND; // Do not trap, it can be used as a query
 success:
    VERBOSE(DEBUG, "perf_pipedream_event_name_to_code(%s, %p) => event_code: %d", event_name, event_code, *event_code);
    return PERFPIPEDREAM_SUCCESS;
}

int perf_pipedream_create_eventset(int *event_set) {
    VERBOSE(DEBUG, "perf_pipedream_create_event_set(%p): initial: %d", event_set, *event_set);
    if (UNFREQUENT(*event_set != PERFPIPEDREAM_NULL))
        return MAY_TRAP(TRAP, PERFPIPEDREAM_EEVENTSET_NOTNULL);

    for (int i = 0; i < NUM_EVENT_SET; ++i) {
        if (ALL_EVENT_SET[i] == EVENTSET_FREE) {
            ALL_EVENT_SET[i] = NULL;
            NUM_PE[i] = 0;
            *event_set = i + 1;
            goto success;
        }
    }
    NUM_EVENT_SET++;
    *event_set = NUM_EVENT_SET;
    ALL_EVENT_SET = realloc(ALL_EVENT_SET, sizeof(*ALL_EVENT_SET) * NUM_EVENT_SET);
    NUM_PE = realloc(NUM_PE, sizeof(*NUM_PE) * NUM_EVENT_SET);
    ALL_EVENT_SET[NUM_EVENT_SET - 1] = NULL;
    NUM_PE[NUM_EVENT_SET - 1] = 0;

 success:
    VERBOSE(DEBUG, "perf_pipedream_create_event_set(%p) => event_set: %d", event_set, *event_set);
    return PERFPIPEDREAM_SUCCESS;
}

int perf_pipedream_add_event(int event_set, int event_idx) {
    VERBOSE(DEBUG, "perf_pipedream_add_event(%d, %d)", event_set, event_idx);
    if (UNFREQUENT(event_set == PERFPIPEDREAM_NULL))
        return MAY_TRAP(TRAP, PERFPIPEDREAM_EEVENTSET_NULL);
    if (UNFREQUENT(RUNNING == event_set))
        return MAY_TRAP(TRAP, PERFPIPEDREAM_EEVENT_SET_RUNNING);
    event_set--;
    if (UNFREQUENT(event_set < 0) ||
	UNFREQUENT(event_set >= NUM_EVENT_SET) ||
	UNFREQUENT(ALL_EVENT_SET[event_set] == EVENTSET_FREE))
        return MAY_TRAP(TRAP, PERFPIPEDREAM_EEVENTSET_NOTFOUND);

    for (int i = 0; i < NUM_PE[event_set]; ++i)
        if (ALL_EVENT_SET[event_set][i] == event_idx)
            return MAY_TRAP(TRAP, PERFPIPEDREAM_EEVENT_ALREADY_EXISTS);
    NUM_PE[event_set]++;
    ALL_EVENT_SET[event_set] = realloc(
                                       ALL_EVENT_SET[event_set],
                                       sizeof(*ALL_EVENT_SET[event_set]) * NUM_PE[event_set]);
    ALL_EVENT_SET[event_set][NUM_PE[event_set] - 1] = event_idx;
    if (UNFREQUENT(DEBUG)) {
        const char *buffer = SPRINT_LIST(alloca(sizeof(char)*4096),
                                         4096,
                                         NUM_PE[event_set],
                                         ALL_EVENT_SET[event_set]);
        VERBOSE(DEBUG, "perf_pipedream_add_event(%d, %d) => events: {%s}", event_set + 1, event_idx, buffer);
    }
    return PERFPIPEDREAM_SUCCESS;
}

int perf_pipedream_remove_event(int event_set, int event_idx) {
    VERBOSE(DEBUG, "perf_pipedream_remove_event(%d, %d)", event_set, event_idx);
    if (UNFREQUENT(event_set == PERFPIPEDREAM_NULL))
        return MAY_TRAP(TRAP, PERFPIPEDREAM_EEVENTSET_NULL);
    if (UNFREQUENT(RUNNING == event_set))
        return MAY_TRAP(TRAP, PERFPIPEDREAM_EEVENT_SET_RUNNING);
    event_set--;
    if (UNFREQUENT(event_set < 0) ||
	UNFREQUENT(event_set >= NUM_EVENT_SET) ||
	UNFREQUENT(ALL_EVENT_SET[event_set] == EVENTSET_FREE))
        return MAY_TRAP(TRAP, PERFPIPEDREAM_EEVENTSET_NOTFOUND);

    int found = 0;
    for (int i = 0; i < NUM_PE[event_set]; ++i) {
        if (ALL_EVENT_SET[event_set][i] == event_idx) {
            NUM_PE[event_set]--;
            found = 1;
        }
        if (found && i < NUM_PE[event_set])
            ALL_EVENT_SET[event_set][i] = ALL_EVENT_SET[event_set][i + 1];
    }
    if (!found)
        return MAY_TRAP(TRAP, PERFPIPEDREAM_EEVENT_NOT_IN_SET);

    if (NUM_PE[event_set] == 0) {
      free(ALL_EVENT_SET[event_set]);
      ALL_EVENT_SET[event_set] = NULL;
    }

    if (UNFREQUENT(DEBUG)) {
        const char *buffer = SPRINT_LIST(alloca(sizeof(char)*4096),
                                         4096,
                                         NUM_PE[event_set],
                                         ALL_EVENT_SET[event_set]);
        VERBOSE(DEBUG, "perf_pipedream_remove_event(%d, %d) => events: {%s}", event_set + 1, event_idx, buffer);
    }
    return PERFPIPEDREAM_SUCCESS;
}

int perf_pipedream_start(int event_set) {
    VERBOSE(DEBUG, "perf_pipedream_start(%d)", event_set);
    if (UNFREQUENT(event_set == PERFPIPEDREAM_NULL))
        return MAY_TRAP(TRAP, PERFPIPEDREAM_EEVENTSET_NULL);
    event_set--;
    if (UNFREQUENT(event_set < 0) ||
	UNFREQUENT(event_set >= NUM_EVENT_SET) ||
	UNFREQUENT(ALL_EVENT_SET[event_set] == EVENTSET_FREE))
        return MAY_TRAP(TRAP, PERFPIPEDREAM_EEVENTSET_NOTFOUND);
    if (UNFREQUENT(RUNNING))
        return MAY_TRAP(TRAP, PERFPIPEDREAM_EALREADY_RUNNING);

    RUNNING = event_set + 1;
    NUM_RUNNING_PE = 0;

    int *events = ALL_EVENT_SET[event_set];
    int num_events = NUM_PE[event_set];
    for (int i = 0; i < num_events; ++i) {
        {
            int event_idx = events[i];
            __u64 config;
            int errcode = event_idx_to_config(event_idx, &config);
            if (errcode != PERFPIPEDREAM_SUCCESS)
                return MAY_TRAP(TRAP, errcode);
            NUM_RUNNING_PE++;
            RUNNING_PE = (struct perf_event_attr **)realloc(
                                                            RUNNING_PE, sizeof(struct perf_event_attr *) * NUM_RUNNING_PE);
            struct perf_event_attr *pe = malloc(sizeof(*pe));
            RUNNING_PE[NUM_RUNNING_PE - 1] = pe;

            memset(pe, 0, sizeof(*pe));
            pe->type = PERF_TYPE_HARDWARE;
            pe->size = sizeof(*pe);
            pe->disabled = 1;
            pe->exclude_kernel = 1;
            pe->exclude_hv = 1;
            pe->config = config;

            RUNNING_PE_CONFIG = (s_perf_event_config_t **)realloc(
                                                                  RUNNING_PE_CONFIG, sizeof(s_perf_event_config_t *) * NUM_RUNNING_PE);
            RUNNING_PE_CONFIG[NUM_RUNNING_PE - 1] = malloc(sizeof(s_perf_event_config_t));
            s_perf_event_config_t *pe_config = RUNNING_PE_CONFIG[NUM_RUNNING_PE - 1];
            pe_config->fd = perf_event_open(pe, 0, -1, -1, 0);
            if (pe_config->fd == -1)
                return MAY_TRAP(TRAP, PERFPIPEDREAM_EPERF_OPEN);
        }
    }
    for (int i = 0; i < NUM_RUNNING_PE; ++i)
        ioctl(RUNNING_PE_CONFIG[i]->fd, PERF_EVENT_IOC_RESET, 0);

    for (int i = 0; i < NUM_RUNNING_PE; ++i)
        ioctl(RUNNING_PE_CONFIG[i]->fd, PERF_EVENT_IOC_ENABLE, 0);

    if (UNFREQUENT(DEBUG)) {
        int *fds = alloca(sizeof(int)*NUM_RUNNING_PE);
        for (int i = 0; i < NUM_RUNNING_PE; ++i)
            fds[i] = RUNNING_PE_CONFIG[i]->fd;
        const char *buffer = SPRINT_LIST(alloca(sizeof(char)*4096),
                                         4096,
                                         NUM_RUNNING_PE,
                                         fds);
        VERBOSE(DEBUG, "perf_pipedream_start(%d) => fds: {%s}", event_set + 1, buffer);
    }
    return PERFPIPEDREAM_SUCCESS;
}

int perf_pipedream_stop(int event_set, long_long res[]) {
    VERBOSE(DEBUG, "perf_pipedream_stop(%d, %p)", event_set, res);
    if (UNFREQUENT(event_set == PERFPIPEDREAM_NULL))
        return MAY_TRAP(TRAP, PERFPIPEDREAM_EEVENTSET_NULL);
    event_set--;
    if (UNFREQUENT(event_set < 0) ||
	UNFREQUENT(event_set >= NUM_EVENT_SET) ||
	UNFREQUENT(ALL_EVENT_SET[event_set] == EVENTSET_FREE))
        return MAY_TRAP(TRAP, PERFPIPEDREAM_EEVENTSET_NOTFOUND);
    if (UNFREQUENT(RUNNING != event_set + 1))
        return MAY_TRAP(TRAP, PERFPIPEDREAM_ENOT_RUNNING);

    if (res != NULL) {
        for (int i = 0; i < NUM_RUNNING_PE; ++i) {
            read(RUNNING_PE_CONFIG[i]->fd, res + i, sizeof(*res));
        }
        if (UNFREQUENT(DEBUG)) {
            const char *buffer = SPRINT_LIST(alloca(sizeof(char)*4096),
                                             4096,
                                             NUM_RUNNING_PE,
                                             res);
            VERBOSE(DEBUG, "perf_pipedream_stop(%d, %p): results: {%s}", event_set + 1, res, buffer);
        }
    }

    for (int i = 0; i < NUM_RUNNING_PE; ++i) {
        ioctl(RUNNING_PE_CONFIG[i]->fd, PERF_EVENT_IOC_DISABLE, 0);
        close(RUNNING_PE_CONFIG[i]->fd);
        free(RUNNING_PE_CONFIG[i]);
        free(RUNNING_PE[i]);
    }

    free(RUNNING_PE);
    RUNNING_PE = NULL;
    free(RUNNING_PE_CONFIG);
    RUNNING_PE_CONFIG = NULL;
    NUM_RUNNING_PE = 0;
    RUNNING = 0;

    return PERFPIPEDREAM_SUCCESS;
}

int perf_pipedream_read(int event_set, long_long res[]) {
    VERBOSE(DEBUG, "perf_pipedream_read(%d, %p)", event_set, res);
    if (UNFREQUENT(event_set == PERFPIPEDREAM_NULL))
        return MAY_TRAP(TRAP, PERFPIPEDREAM_EEVENTSET_NULL);
    event_set--;
    if (UNFREQUENT(event_set < 0) ||
	UNFREQUENT(event_set >= NUM_EVENT_SET) ||
	UNFREQUENT(ALL_EVENT_SET[event_set] == EVENTSET_FREE))
        return MAY_TRAP(TRAP, PERFPIPEDREAM_EEVENTSET_NOTFOUND);
    if (UNFREQUENT(RUNNING != event_set + 1))
        return MAY_TRAP(TRAP, PERFPIPEDREAM_ENOT_RUNNING);

    if (res != NULL) {
        for (int i = 0; i < NUM_RUNNING_PE; ++i) {
            read(RUNNING_PE_CONFIG[i]->fd, res + i, sizeof(*res));
        }
        if (UNFREQUENT(DEBUG)) {
            const char *buffer = SPRINT_LIST(alloca(sizeof(char)*4096),
                                             4096,
                                             NUM_RUNNING_PE,
                                             res);
            VERBOSE(DEBUG, "perf_pipedream_read(%d, %p): results: {%s}", event_set + 1, res, buffer);
        }
    }

    return PERFPIPEDREAM_SUCCESS;
}

int perf_pipedream_cleanup_eventset(int event_set) {
    VERBOSE(DEBUG, "perf_pipedream_cleanup_event_set(%d)", event_set);
    if (UNFREQUENT(event_set == PERFPIPEDREAM_NULL))
        return MAY_TRAP(TRAP, PERFPIPEDREAM_EEVENTSET_NULL);
    if (UNFREQUENT(RUNNING == event_set))
        return MAY_TRAP(TRAP, PERFPIPEDREAM_EEVENT_SET_RUNNING);
    event_set--;
    if (UNFREQUENT(event_set < 0) ||
	UNFREQUENT(event_set >= NUM_EVENT_SET) ||
	UNFREQUENT(ALL_EVENT_SET[event_set] == EVENTSET_FREE))
        return MAY_TRAP(TRAP, PERFPIPEDREAM_EEVENTSET_NOTFOUND);
    free(ALL_EVENT_SET[event_set]);
    ALL_EVENT_SET[event_set] = NULL;
    NUM_PE[event_set] = 0;
    return PERFPIPEDREAM_SUCCESS;
}

int perf_pipedream_destroy_eventset(int *event_set) {
    VERBOSE(DEBUG, "perf_pipedream_destroy_event_set(%p): value: %d", event_set, *event_set);
    if (UNFREQUENT(*event_set == PERFPIPEDREAM_NULL))
        return MAY_TRAP(TRAP, PERFPIPEDREAM_EEVENTSET_NULL);
    if (UNFREQUENT(RUNNING == *event_set))
        return MAY_TRAP(TRAP, PERFPIPEDREAM_EEVENT_SET_RUNNING);
    *event_set = *event_set - 1;
    if (UNFREQUENT(*event_set < 0) ||
	UNFREQUENT(*event_set >= NUM_EVENT_SET) ||
	UNFREQUENT(ALL_EVENT_SET[*event_set] == EVENTSET_FREE)) {
        *event_set = *event_set + 1;
        return MAY_TRAP(TRAP, PERFPIPEDREAM_EEVENTSET_NOTFOUND);
    }
    if (ALL_EVENT_SET[*event_set] != NULL)
        perf_pipedream_cleanup_eventset(*event_set + 1);
    ALL_EVENT_SET[*event_set] = EVENTSET_FREE;
    *event_set = PERFPIPEDREAM_NULL;
    return PERFPIPEDREAM_SUCCESS;
}
