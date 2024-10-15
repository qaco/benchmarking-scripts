#define PERFPIPEDREAM_CURRENT_VERSION (1)

#define PERFPIPEDREAM_SUCCESS (0)
#define PERFPIPEDREAM_EEVENT_NOTFOUND (-1)
#define PERFPIPEDREAM_ENO_EVENT_IDX (-2)
#define PERFPIPEDREAM_EPERF_OPEN (-3)
#define PERFPIPEDREAM_EEVENT_ALREADY_EXISTS (-4)
#define PERFPIPEDREAM_EALREADY_RUNNING (-5)
#define PERFPIPEDREAM_ENOT_RUNNING (-6)
#define PERFPIPEDREAM_EEVENTSET_NOTFOUND (-7)
#define PERFPIPEDREAM_EEVENTSET_NONEMPTY (-8)
#define PERFPIPEDREAM_EEVENTSET_NOTNULL (-9)
#define PERFPIPEDREAM_EALREADY_INIT (-10)
#define PERFPIPEDREAM_EINVALID_VERSION (-11)
#define PERFPIPEDREAM_EEVENT_NOT_IN_SET (-12)
#define PERFPIPEDREAM_EEVENT_SET_RUNNING (-13)
#define PERFPIPEDREAM_EEVENTSET_NULL (-14)

#define PERFPIPEDREAM_NULL (-1)

#define long_long long long

const char *perf_pipedream_strerror(int errcode);
int perf_pipedream_query_event(int event_code);
int perf_pipedream_library_init(int version);
int perf_pipedream_is_initialized();
int perf_pipedream_event_name_to_code(const char *event_name, int *event_code);
int perf_pipedream_create_eventset(int *event_set);
int perf_pipedream_add_event(int event_set, int event_idx);
int perf_pipedream_remove_event(int event_set, int event_idx);
int perf_pipedream_start(int event_set);
int perf_pipedream_read(int event_set, long long res[]);
int perf_pipedream_stop(int event_set, long long res[]);
int perf_pipedream_cleanup_eventset(int event_set);
int perf_pipedream_destroy_eventset(int *event_set);
void perf_pipedream_shutdown();
