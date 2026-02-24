import { useConfigStore } from "@/stores/config";
import { storeToRefs } from "pinia";

export function useSkipEmailWorkflow() {
  return storeToRefs(useConfigStore());
}
