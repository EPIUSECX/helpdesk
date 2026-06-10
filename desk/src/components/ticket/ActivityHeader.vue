<template>
  <div
    class="md:mx-5 md:my-4 flex items-center justify-between text-lg font-medium mx-6 !mb-0 !my-3"
  >
    <div class="flex h-8 items-center text-xl font-semibold text-ink-gray-8">
      {{ title }}
    </div>
    <Button
      v-if="title == 'Emails' && !skipEmailWorkflow"
      variant="subtle"
      @click="communicationAreaRef?.toggleEmailBox() ?? toggleEmailBox()"
    >
      <template #prefix>
        <FeatherIcon name="plus" class="h-4 w-4" />
      </template>
      <span>{{ __("New Email") }}</span>
    </Button>
    <Button
      v-else-if="title == 'Comments'"
      variant="subtle"
      @click="communicationAreaRef?.toggleCommentBox() ?? toggleCommentBox()"
    >
      <template #prefix>
        <FeatherIcon name="plus" class="h-4 w-4" />
      </template>
      <span>{{ __("New Comment") }}</span>
    </Button>
    <Dropdown
      v-else-if="title == 'Calls'"
      :options="callActions"
      @click.stop
      placement="right"
    >
      <template v-slot="{ open }">
        <Button variant="subtle" class="flex items-center gap-1">
          <template #prefix>
            <FeatherIcon name="plus" class="h-4 w-4" />
          </template>
          <span>{{ __("New") }}</span>
          <template #suffix>
            <FeatherIcon
              :name="open ? 'chevron-up' : 'chevron-down'"
              class="h-4 w-4"
            />
          </template>
        </Button>
      </template>
    </Dropdown>
    <Dropdown
      v-else-if="title != 'Emails'"
      :options="defaultActions"
      @click.stop
      placement="right"
    >
      <template v-slot="{ open }">
        <Button variant="subtle" class="flex items-center gap-1">
          <template #prefix>
            <FeatherIcon name="plus" class="h-4 w-4" />
          </template>
          <span>{{ __("New") }}</span>
          <template #suffix>
            <FeatherIcon
              :name="open ? 'chevron-up' : 'chevron-down'"
              class="h-4 w-4"
            />
          </template>
        </Button>
      </template>
    </Dropdown>
  </div>
  <CallLogModal
    v-model="showCallLogModal"
    :ticketId="ticket.value?.doc?.name"
    @after-insert="refreshTicket"
  />
</template>

<script setup lang="ts">
import { useActivityHeaderActions } from "@/composables/useActivityHeaderActions";
import { useSkipEmailWorkflow } from "@/composables/useSkipEmailWorkflow";
import CallLogModal from "@/pages/call-logs/CallLogModal.vue";
import { useTelephonyStore } from "@/stores/telephony";
import { toggleCommentBox, toggleEmailBox } from "@/pages/ticket/modalStates";
import { __ } from "@/translation";
import { TicketSymbol } from "@/types";
import { Dropdown } from "frappe-ui";
import { storeToRefs } from "pinia";
import { computed, h, inject, ref, type Ref } from "vue";
import { PhoneIcon } from "@/components/icons";

type CommunicationAreaRef = {
  toggleEmailBox: () => void;
  toggleCommentBox: () => void;
};

defineProps({
  title: {
    type: String,
    required: true,
  },
});

const communicationAreaRef = inject<Ref<CommunicationAreaRef | null>>(
  "communicationArea",
  ref(null)
);
const makeCall = inject<() => void>("makeCall");
const refreshTicket = inject<() => void>("refreshTicket");
const showCallLogModal = ref(false);
const { isCallingEnabled } = storeToRefs(useTelephonyStore());
const { skipEmailWorkflow } = useSkipEmailWorkflow();
const ticket = inject(TicketSymbol)!;

const { defaultActions, callActions } = useActivityHeaderActions({
  communicationAreaRef,
  isCallingEnabled,
  toggleEmailBox,
  toggleCommentBox,
  makeCall: makeCall ?? (() => {}),
  showCallLogModal,
});
</script>

<style scoped></style>
