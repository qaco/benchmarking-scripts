#include <stdio.h>
#include <stdlib.h>

#include "perf-pipedream.h"

static void handle(int ret) {
    if (ret != PERFPIPEDREAM_SUCCESS) {
        fprintf(stderr, "Error: %s\n", perf_pipedream_strerror(ret));
        exit(EXIT_FAILURE);
    }
}

static void init() {
    int ret = perf_pipedream_library_init(PERFPIPEDREAM_CURRENT_VERSION);
    if (ret < 0)
        handle(ret);
    if (ret != PERFPIPEDREAM_CURRENT_VERSION) {
        fprintf(stderr, "Error: bad version %d, expeted %d\n", ret, PERFPIPEDREAM_CURRENT_VERSION);
        exit(EXIT_FAILURE);
    }
}

static void create(int *events_ptr) {
    *events_ptr = PERFPIPEDREAM_NULL;
    int ret = perf_pipedream_create_eventset(events_ptr);
    handle(ret);
}

static void cleanup(int events) {
    int ret = perf_pipedream_cleanup_eventset(events);
    handle(ret);
}

static void destroy(int *events_ptr) {
    int ret = perf_pipedream_destroy_eventset(events_ptr);
    handle(ret);
}

static void shutdown() {
    perf_pipedream_shutdown();
}

static void add_event(int events, int event_code) {
    int ret = perf_pipedream_add_event(events, event_code);
    handle(ret);
}

static void remove_event(int events, int event_code) {
    int ret = perf_pipedream_remove_event(events, event_code);
    handle(ret);
}

static int event_name_code(const char *event_name) {
    int event_code;
    int ret = perf_pipedream_event_name_to_code(event_name, &event_code);
    handle(ret);
    return event_code;
}

static void add_event_name(int events, const char *event_name) {
    int event_code = event_name_code(event_name);
    add_event(events, event_code);
}

static void start(int events) {
    int ret = perf_pipedream_start(events);
    handle(ret);
}

static void stop(int events, long long int values[]) {
    int ret = perf_pipedream_stop(events, values);
    handle(ret);
}

static void read(int events, long long int values[]) {
    int ret = perf_pipedream_read(events, values);
    handle(ret);
}


#define PRINTF(...) do { printf(__VA_ARGS__); fflush(stdout); } while(0)
#define MAX_SIZE 100000

int main() {

    int events;

    init();
    create(&events);

    add_event_name(events, "PAPI_TOT_CYC");
    int event_code_ins = event_name_code("PAPI_TOT_INS");
    int event_code_cyc = event_name_code("PAPI_TOT_CYC");

    int *A = malloc(MAX_SIZE * sizeof(*A));
    int *B = malloc(MAX_SIZE * sizeof(*B));

    A[0] = 4;
    B[0] = 8;
    for (int i = 1; i < MAX_SIZE; ++i) {
        A[i] = (A[i - 1] * 42) % 405;
        B[i] = (A[i] * 56) % 308;
    }

    long long values[2];
    long long num_reps = 1000;
    int num_execs = 5;
    for (int e = 0; e < num_execs; ++e) {
        long long num_its, num_rounds;
        if (num_reps > MAX_SIZE) {
            num_its = MAX_SIZE;
            num_rounds = num_reps / MAX_SIZE;
        } else {
            num_its = num_reps;
            num_rounds = 1;
        }
        add_event(events, event_code_ins);
        start(events);

        PRINTF("Running: %lld...\n", num_rounds * num_its);
        for (long long r = 0; r < num_rounds; r++) {
            for (long long i = 0; i < num_its; ++i) {
                B[i] = A[i] * B[i];
            }
        }

        // Test stop and read
        if (e % 2) {
            stop(events, values);
        } else {
            read(events, values);
            stop(events, NULL);
        }

        remove_event(events, event_code_ins);

        // Test shutdown/restart and cleanup/add
        if (e == 0) {
            shutdown();
            init();
            create(&events);
            add_event_name(events, "PAPI_TOT_CYC");
        } else if (e == 1) {
            cleanup(events);
            add_event_name(events, "PAPI_TOT_CYC");
        } else if (e == 2) {
            destroy(&events);
            create(&events);
            add_event_name(events, "PAPI_TOT_CYC");
        } else if (e == 3) {
	    remove_event(events, event_code_cyc);
	    cleanup(events);
            add_event(events, event_code_cyc);
        }

        // Avoid DCE
        *((volatile int *)&B[rand()*(MAX_SIZE-1)/RAND_MAX]);

        PRINTF("Num reps:   %lld\n"
               "Num cycles: %lld\n"
               "Num instrs: %lld\n"
               "IPC:        %f\n",
               num_its * num_rounds, values[0], values[1], ((float)values[1]) / values[0]);
        num_reps *= 10;
        if (e < num_execs - 1)
            PRINTF("\n");
    }

    free(A);
    free(B);

    cleanup(events);
    destroy(&events);

    perf_pipedream_shutdown();
    return 0;
}
