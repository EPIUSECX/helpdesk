import { CommentIcon, EmailIcon, PhoneIcon } from "@/components/icons";
import { __ } from "@/translation";
import { computed, h, type Ref } from "vue";

import { useSkipEmailWorkflow } from "./useSkipEmailWorkflow";

export interface UseActivityHeaderActionsOptions {
  communicationAreaRef: Ref<{ toggleEmailBox: () => void; toggleCommentBox: () => void } | null>;
  isCallingEnabled: Ref<boolean>;
  toggleEmailBox: () => void;
  toggleCommentBox: () => void;
  makeCall: () => void;
  showCallLogModal: Ref<boolean>;
}

export function useActivityHeaderActions(
  options: UseActivityHeaderActionsOptions
) {
  const { skipEmailWorkflow } = useSkipEmailWorkflow();
  const {
    communicationAreaRef,
    isCallingEnabled,
    toggleEmailBox,
    toggleCommentBox,
    makeCall,
    showCallLogModal,
  } = options;

  const callActions = computed(() => [
    {
      icon: h(PhoneIcon, { class: "h-4 w-4" }),
      label: __("Make a Call"),
      onClick: () => makeCall(),
    },
    {
      icon: "edit-3",
      label: __("Log a Call"),
      onClick: () => {
        showCallLogModal.value = true;
      },
    },
  ]);

  const defaultActions = computed(() => {
    const actions = [
      ...(skipEmailWorkflow.value
        ? []
        : [
            {
              icon: h(EmailIcon, { class: "h-4 w-4" }),
              label: __("Email"),
              onClick: () =>
                communicationAreaRef?.value?.toggleEmailBox() ?? toggleEmailBox(),
            },
          ]),
      {
        icon: h(CommentIcon, { class: "h-4 w-4" }),
        label: __("Comment"),
        onClick: () =>
          communicationAreaRef?.value?.toggleCommentBox() ??
          toggleCommentBox(),
      },
    ];

    if (isCallingEnabled.value) {
      actions.push(...callActions.value);
    }

    return actions;
  });

  return { defaultActions, callActions };
}
