import {
  ActivityIcon,
  CommentIcon,
  EmailIcon,
  PhoneIcon,
} from "@/components/icons";
import type { TabObject } from "@/types";
import { computed, type Ref } from "vue";

import { useSkipEmailWorkflow } from "./useSkipEmailWorkflow";

export function useActivityTabs(isCallingEnabled: Ref<boolean>) {
  const { skipEmailWorkflow } = useSkipEmailWorkflow();

  return computed(() => {
    const _tabs: TabObject[] = [
      { name: "activity", label: "Activity", icon: ActivityIcon },
      ...(skipEmailWorkflow.value
        ? []
        : [{ name: "email" as const, label: "Emails", icon: EmailIcon }]),
      { name: "comment", label: "Comments", icon: CommentIcon },
    ];

    if (isCallingEnabled.value) {
      _tabs.push({ name: "call", label: "Calls", icon: PhoneIcon });
    }
    return _tabs;
  });
}

export interface UseActivityTabsMobileOptions {
  isMobileView: Ref<boolean>;
  DetailsIcon: unknown;
}

export function useActivityTabsMobile(
  isCallingEnabled: Ref<boolean>,
  options: UseActivityTabsMobileOptions
) {
  const { skipEmailWorkflow } = useSkipEmailWorkflow();
  const { isMobileView, DetailsIcon } = options;

  return computed(() => {
    const _tabs: TabObject[] = [
      {
        name: "details",
        label: __("Details"),
        icon: DetailsIcon,
        condition: () => isMobileView.value,
      },
      { name: "activity", label: __("Activity"), icon: ActivityIcon },
      ...(skipEmailWorkflow.value
        ? []
        : [{ name: "email" as const, label: __("Emails"), icon: EmailIcon }]),
      { name: "comment", label: __("Comments"), icon: CommentIcon },
    ];

    if (isCallingEnabled.value) {
      _tabs.push({ name: "call", label: __("Calls"), icon: PhoneIcon });
    }
    return _tabs;
  });
}
