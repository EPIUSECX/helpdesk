<template>
  <Autocomplete
    v-if="!sortValues?.size"
    :options="options"
    value=""
    :placeholder="'First Name'"
    @change="(e) => setSort(e)"
  >
    <template #target="{ togglePopover }">
      <Button :label="__('Sort')" @click="togglePopover()">
        <template v-if="hideLabel" #icon>
          <SortIcon class="h-4" />
        </template>
        <template v-else-if="!sortValues?.size" #prefix>
          <SortIcon class="h-4" />
        </template>
      </Button>
    </template>
  </Autocomplete>
  <NestedPopover v-else>
    <template #target="{ open }">
      <Button v-if="sortValues.size > 1" :label="__('Sort')">
        <template v-if="hideLabel" #icon>
          <SortIcon class="h-4" />
        </template>
        <template v-else #prefix><SortIcon class="h-4" /></template>
        <template v-if="sortValues?.size" #suffix>
          <div
            class="flex h-5 w-5 items-center justify-center rounded-[5px] bg-surface-white pt-px text-xs font-medium text-ink-gray-8 shadow-sm"
          >
            {{ sortValues.size }}
          </div>
        </template>
      </Button>
      <div v-else class="flex items-center justify-center">
        <Button
          v-if="sortValues.size"
          class="rounded-e-none border-e"
          @click.stop="
            () => {
              sortItems[0].direction =
                sortItems[0].direction == 'asc' ? 'desc' : 'asc';
              apply();
            }
          "
        >
          <AscendingIcon v-if="sortItems[0].direction == 'asc'" class="h-4" />
          <DescendingIcon v-else class="h-4" />
        </Button>
        <Button
          :label="getSortLabel()"
          :class="sortValues.size ? 'rounded-s-none' : ''"
        >
          <template v-if="!hideLabel && !sortValues?.size" #prefix>
            <SortIcon class="h-4" />
          </template>
          <template v-if="sortValues?.size" #suffix>
            <FeatherIcon
              :name="open ? 'chevron-up' : 'chevron-down'"
              class="h-4 text-ink-gray-5"
            />
          </template>
        </Button>
      </div>
    </template>
    <template #body="{ close }">
      <div
        class="my-2 rounded-lg border border-outline-gray-1 bg-surface-white shadow-xl"
      >
        <div class="min-w-60 p-2">
          <div
            v-if="sortValues?.size"
            id="sort-list"
            class="mb-3 flex flex-col gap-2"
          >
            <div
              v-for="(sort, i) in sortItems"
              :key="sort.fieldname"
              class="flex items-center gap-1"
            >
              <div class="handle flex h-7 w-7 items-center justify-center">
                <DragIcon class="h-4 w-4 cursor-grab text-ink-gray-5" />
              </div>
              <div class="flex">
                <Button
                  size="md"
                  class="rounded-e-none border-e"
                  @click="
                    () => {
                      sort.direction = sort.direction == 'asc' ? 'desc' : 'asc';
                      apply();
                    }
                  "
                >
                  <AscendingIcon v-if="sort.direction == 'asc'" class="h-4" />
                  <DescendingIcon v-else class="h-4" />
                </Button>
                <Autocomplete
                  class="!w-32"
                  :value="sort.fieldname"
                  :options="sortOptions.data"
                  @change="(e) => updateSort(e, i)"
                  :placeholder="'First Name'"
                >
                  <template
                    #target="{ togglePopover, selectedValue, displayValue }"
                  >
                    <Button
                      class="flex w-full items-center justify-between rounded-s-none !text-ink-gray-5 text-xs"
                      size="md"
                      @click="togglePopover()"
                    >
                      {{ __(displayValue(selectedValue)) }}
                      <template #suffix>
                        <FeatherIcon
                          name="chevron-down"
                          class="h-4 text-ink-gray-5"
                        />
                      </template>
                    </Button>
                  </template>
                </Autocomplete>
              </div>
              <Button variant="ghost" icon="lucide-x" @click="removeSort(i)" />
            </div>
          </div>
          <div
            v-else
            class="mb-3 flex h-7 items-center px-3 text-sm text-ink-gray-5"
          >
            {{ __("Empty - Choose a field to sort by") }}
          </div>
          <div class="flex items-center justify-between gap-2">
            <Autocomplete
              :options="options"
              value=""
              :placeholder="'First Name'"
              @change="(e) => setSort(e)"
            >
              <template #target="{ togglePopover }">
                <Button
                  class="!text-ink-gray-5"
                  variant="ghost"
                  @click="togglePopover()"
                  :label="__('Add Sort')"
                >
                  <template #prefix>
                    <FeatherIcon name="plus" class="h-4" />
                  </template>
                </Button>
              </template>
            </Autocomplete>
            <Button
              v-if="sortValues?.size"
              class="!text-ink-gray-5"
              variant="ghost"
              :label="__('Clear Sort')"
              @click="clearSort(close)"
            />
          </div>
        </div>
      </div>
    </template>
  </NestedPopover>
</template>

<script setup>
import { computed, inject, nextTick, ref, watch } from "vue";
import { NestedPopover } from "frappe-ui";
import { useSortable } from "@vueuse/integrations/useSortable";
import Autocomplete from "@/components/frappe-ui/Autocomplete.vue";
import {
  AscendingIcon,
  DescendingIcon,
  SortIcon,
  DragIcon,
} from "@/components/icons";

const props = defineProps({
  hideLabel: {
    type: Boolean,
    default: false,
  },
});

const emit = defineEmits(["update"]);

const listViewData = inject("listViewData");
const listViewActions = inject("listViewActions");
const { list, sortableFields: sortOptions } = listViewData;

// Parse an order_by string into an array of { fieldname, direction } objects.
function parseOrderBy(orderBy) {
  if (!orderBy || !sortOptions.data) return [];
  return orderBy.split(", ").map((sortValue) => {
    const [fieldname, direction] = sortValue.split(" ");
    return { fieldname, direction };
  });
}

// Serialise sortItems to the same format as order_by for equality checks.
function serialise(items) {
  return items.map((f) => `${f.fieldname} ${f.direction}`).join(", ");
}

// Reactive array — single source of truth for the current sort state.
// useSortable mutates this array in-place on drag-end (via moveArrayElement),
// so apply() always reads the post-drag order.
const sortItems = ref(parseOrderBy(list?.params?.order_by));

// Guard flag: when true the order_by watch skips re-parsing because the
// change originated from apply() and sortItems already holds the correct
// post-action state.  Cleared on the next tick after the reactive flush.
let _selfUpdate = false;

// Sync sortItems when order_by changes externally (view switch, reload).
// Skip when the parsed result is identical to the current state — this
// prevents useSortable's array reference from being replaced after
// onSuccess reassigns list.params, which would break drag-reorder and
// cause direction toggles to require two clicks.
watch(
  () => list?.params?.order_by,
  (orderBy) => {
    if (_selfUpdate) return;
    const parsed = parseOrderBy(orderBy);
    if (serialise(parsed) === serialise(sortItems.value)) return;
    sortItems.value = parsed;
    nextTick(restartSort);
  },
);

// Parse the initial order_by once the field list arrives (it may load after
// the component mounts).
watch(
  () => sortOptions.data,
  () => {
    if (_selfUpdate) return;
    const parsed = parseOrderBy(list?.params?.order_by);
    if (serialise(parsed) === serialise(sortItems.value)) return;
    sortItems.value = parsed;
    nextTick(restartSort);
  },
);

// Thin shim so the template's sortValues.size checks continue to work.
const sortValues = computed(() => ({
  size: sortItems.value.length,
}));

// Pure computed — no side effects. restartSort() is called explicitly where
// needed (setSort) so Sortable picks up newly added DOM nodes.
const options = computed(() => {
  if (!sortOptions.data) return [];
  if (!sortItems.value.length) return sortOptions.data;
  const selectedOptions = sortItems.value.map((sort) => sort.fieldname);
  return sortOptions.data.filter((option) => {
    return !selectedOptions.includes(option.value);
  });
});

// useSortable operates on the reactive array; its internal onEnd handler calls
// moveArrayElement(sortItems.value, oldIndex, newIndex) before invoking the
// user onEnd callback (via nextTick), so apply() always sees the post-drag order.
const sortSortable = useSortable("#sort-list", sortItems, {
  handle: ".handle",
  animation: 200,
  onEnd: () => apply(),
});

function getSortLabel() {
  if (!sortItems.value.length) return "Sort";
  const first = sortItems.value[0];
  const label = sortOptions.data?.find(
    (option) => option.value === first.fieldname,
  )?.label;
  return label || first.fieldname;
}

function setSort(data) {
  sortItems.value.push({ fieldname: data.value, direction: "asc" });
  // Restart so Sortable picks up the newly rendered DOM node.
  restartSort();
  apply();
}

function updateSort(data, index) {
  const old = sortItems.value[index];
  sortItems.value.splice(index, 1, {
    fieldname: data.value,
    direction: old.direction,
  });
  apply();
}

function removeSort(index) {
  sortItems.value.splice(index, 1);
  apply();
}

function clearSort(close) {
  sortItems.value = [];
  apply();
  close();
}

function apply() {
  const orderBy = convertToString(sortItems.value);
  // Set the guard so the order_by watch does not overwrite sortItems.
  _selfUpdate = true;
  listViewActions.applySort(orderBy);
  // Clear the guard after the reactive flush completes.
  nextTick(() => {
    _selfUpdate = false;
  });
}

function convertToString(values) {
  return values.map((f) => `${f.fieldname} ${f.direction}`).join(", ");
}

function restartSort() {
  sortSortable.stop();
  sortSortable.start();
}
</script>
