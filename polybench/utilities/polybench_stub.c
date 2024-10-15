#include <stdlib.h>
#include "polybench.h"

#define POLYBENCH_MAX_NB_PPAPI_COUNTERS 96

int polybench_papi_eventlist[POLYBENCH_MAX_NB_PPAPI_COUNTERS] = {0,1};
void *polybench_alloc_data(unsigned long long int n, int elt_size) {
  size_t val = n;
  val *= elt_size;
  void *ret = malloc(val);
  return ret;
}
void polybench_prepare_instruments() {}
void polybench_papi_init() {}
int polybench_papi_start_counter(int evid) {
  return 0;
}
void polybench_papi_stop_counter(int evid) {}
void polybench_papi_close() {}
void polybench_papi_print() {}
