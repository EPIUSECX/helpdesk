<template>
  <div class="flex flex-col overflow-y-auto">
    <LayoutHeader>
      <template #left-header>
        <Breadcrumbs :items="breadcrumbs" />
      </template>
    </LayoutHeader>

    <div
      class="flex flex-col gap-5 py-6 h-full flex-1 self-center overflow-auto mx-auto w-full max-w-2xl px-5"
    >
      <!-- Page heading -->
      <div>
        <h2 class="text-xl font-semibold text-ink-gray-9">
          {{ __("New Customer Ticket") }}
        </h2>
        <p class="mt-1 text-p-sm text-ink-gray-6">
          {{
            __(
              "Create a support ticket on behalf of a customer. A WhatsApp notification will be sent to the customer automatically."
            )
          }}
        </p>
      </div>

      <!-- Form -->
      <div class="flex flex-col gap-4">
        <!-- Row 1: First name / Last name -->
        <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div class="flex flex-col gap-1.5">
            <label class="text-xs text-ink-gray-5 after:content-['*'] after:ms-0.5 after:text-ink-red-3">
              {{ __("Customer First Name") }}
            </label>
            <FormControl
              v-model="form.firstName"
              type="text"
              :placeholder="__('John')"
            />
          </div>
          <div class="flex flex-col gap-1.5">
            <label class="text-xs text-ink-gray-5 after:content-['*'] after:ms-0.5 after:text-ink-red-3">
              {{ __("Customer Last Name") }}
            </label>
            <FormControl
              v-model="form.lastName"
              type="text"
              :placeholder="__('Doe')"
            />
          </div>
        </div>

        <!-- Row 2: Phone number -->
        <div class="flex flex-col gap-1.5">
          <label class="text-xs text-ink-gray-5 after:content-['*'] after:ms-0.5 after:text-ink-red-3">
            {{ __("Customer Phone Number") }}
          </label>
          <FormControl
            v-model="form.phone"
            type="text"
            :placeholder="__('0821234567 or +27 82 123 4567')"
          />
          <span v-if="normalisedPhone" class="text-xs text-ink-gray-5">
            {{ __("Will be sent as:") }} <span class="font-mono">{{ normalisedPhone }}</span>
          </span>
        </div>

        <!-- Row 3: Store Branch / Ticket Type -->
        <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div class="flex flex-col gap-1.5">
            <label class="text-xs text-ink-gray-5 after:content-['*'] after:ms-0.5 after:text-ink-red-3">
              {{ __("Store Branch (Team)") }}
            </label>
            <Link
              doctype="HD Team"
              :modelValue="form.agentGroup"
              :label="__('Select store branch')"
              size="sm"
              variant="subtle"
              @update:modelValue="form.agentGroup = $event"
            />
          </div>
          <div class="flex flex-col gap-1.5">
            <label class="text-xs text-ink-gray-5 after:content-['*'] after:ms-0.5 after:text-ink-red-3">
              {{ __("Ticket Type") }}
            </label>
            <Link
              doctype="HD Ticket Type"
              :modelValue="form.ticketType"
              :label="__('Select ticket type')"
              size="sm"
              variant="subtle"
              @update:modelValue="form.ticketType = $event"
            />
          </div>
        </div>

        <!-- Row 4: Issue description -->
        <div class="flex flex-col gap-1.5">
          <label class="text-xs text-ink-gray-5 after:content-['*'] after:ms-0.5 after:text-ink-red-3">
            {{ __("Issue Description") }}
          </label>
          <FormControl
            v-model="form.issue"
            type="textarea"
            :rows="4"
            :placeholder="__('Describe the customer\'s issue…')"
          />
        </div>
      </div>

      <!-- Validation message -->
      <div v-if="validationError" class="text-sm text-ink-red-3">
        {{ validationError }}
      </div>

      <!-- Actions -->
      <div class="flex justify-end gap-3">
        <RouterLink :to="{ name: 'TicketsAgent' }">
          <Button theme="gray" variant="subtle" :label="__('Cancel')" />
        </RouterLink>
        <Button
          theme="gray"
          variant="solid"
          :label="__('Create Ticket & Notify Customer')"
          :loading="ticket.loading"
          @click="submit"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { LayoutHeader } from "@/components";
import { __ } from "@/translation";
import { Breadcrumbs, Button, FormControl, createResource, usePageMeta } from "frappe-ui";
import { computed, reactive, ref } from "vue";
import { useRouter } from "vue-router";

const router = useRouter();

// ---------------------------------------------------------------------------
// Form state
// ---------------------------------------------------------------------------
const form = reactive({
  firstName: "",
  lastName: "",
  phone: "",
  agentGroup: "",
  ticketType: "",
  issue: "",
});

const validationError = ref("");

// ---------------------------------------------------------------------------
// Phone normalisation preview (client-side, mirrors server logic)
// ---------------------------------------------------------------------------
const normalisedPhone = computed(() => {
  const raw = form.phone.trim();
  if (!raw) return "";
  const digits = raw.replace(/\D/g, "");
  if (!digits) return "";
  if (digits.startsWith("0")) return "27" + digits.slice(1);
  if (!digits.startsWith("27")) return "27" + digits;
  return digits;
});

// ---------------------------------------------------------------------------
// Validation
// ---------------------------------------------------------------------------
function validate(): string {
  if (!form.firstName.trim()) return __("Customer First Name is required");
  if (!form.lastName.trim()) return __("Customer Last Name is required");
  if (!form.phone.trim()) return __("Customer Phone Number is required");
  if (!normalisedPhone.value || normalisedPhone.value.length < 10)
    return __("Please enter a valid phone number");
  if (!form.agentGroup) return __("Store Branch is required");
  if (!form.ticketType) return __("Ticket Type is required");
  if (!form.issue.trim()) return __("Issue Description is required");
  return "";
}

// ---------------------------------------------------------------------------
// Ticket creation — uses the existing hd_ticket.api.new endpoint.
// custom_is_agent_created_for_customer = 1 triggers the server-side logic
// (phone normalisation, subject composition, description prepend, webhook).
// ---------------------------------------------------------------------------
const ticket = createResource({
  url: "helpdesk.helpdesk.doctype.hd_ticket.api.new",
  debounce: 300,
  onSuccess: (data: { name: string }) => {
    router.push({
      name: "TicketAgent",
      params: { ticketId: data.name },
    });
  },
  onError: (err: Error) => {
    validationError.value =
      err?.message || __("An error occurred while creating the ticket.");
  },
});

function submit() {
  validationError.value = validate();
  if (validationError.value) return;

  ticket.submit({
    doc: {
      // Subject is auto-generated server-side from name + ticket type.
      // We pass a temporary placeholder so the field is not empty before
      // before_save runs; the server will overwrite it.
      subject: `${form.firstName} ${form.lastName} - ${form.ticketType}`,
      description: form.issue,
      ticket_type: form.ticketType,
      agent_group: form.agentGroup,
      custom_is_agent_created_for_customer: 1,
      custom_customer_first_name: form.firstName,
      custom_customer_last_name: form.lastName,
      custom_customer_phone: form.phone,
    },
    attachments: [],
  });
}

// ---------------------------------------------------------------------------
// Page meta
// ---------------------------------------------------------------------------
const breadcrumbs = computed(() => [
  {
    label: __("Tickets"),
    route: { name: "TicketsAgent" },
  },
  {
    label: __("New Customer Ticket"),
    route: { name: "TicketNewCustomer" },
  },
]);

usePageMeta(() => ({ title: __("New Customer Ticket") }));
</script>
