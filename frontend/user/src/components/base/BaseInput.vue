<template>
  <div :class="['base-input-wrapper', { 'base-input-wrapper--error': error }]">
    <label v-if="label" class="base-input__label">
      {{ label }}
      <span v-if="required" class="base-input__required">*</span>
    </label>
    <div
      :class="[
        'base-input__container',
        {
          'base-input__container--focused': isFocused,
          'base-input__container--disabled': disabled,
          'base-input__container--readonly': readonly
        }
      ]"
    >
      <span v-if="$slots.prefix" class="base-input__prefix">
        <slot name="prefix" />
      </span>
      <input
        :type="type"
        :value="modelValue"
        :placeholder="placeholder"
        :disabled="disabled"
        :readonly="readonly"
        :required="required"
        :aria-invalid="error ? 'true' : undefined"
        class="base-input"
        @input="$emit('update:modelValue', $event.target.value)"
        @focus="isFocused = true"
        @blur="isFocused = false"
      />
      <span v-if="$slots.suffix" class="base-input__suffix">
        <slot name="suffix" />
      </span>
    </div>
    <p v-if="error" class="base-input__error">{{ error }}</p>
    <p v-else-if="hint" class="base-input__hint">{{ hint }}</p>
  </div>
</template>

<script setup>
import { ref } from 'vue'

defineProps({
  modelValue: {
    type: [String, Number],
    default: ''
  },
  label: {
    type: String,
    default: ''
  },
  placeholder: {
    type: String,
    default: ''
  },
  type: {
    type: String,
    default: 'text'
  },
  disabled: {
    type: Boolean,
    default: false
  },
  readonly: {
    type: Boolean,
    default: false
  },
  required: {
    type: Boolean,
    default: false
  },
  error: {
    type: String,
    default: ''
  },
  hint: {
    type: String,
    default: ''
  }
})

defineEmits(['update:modelValue'])

const isFocused = ref(false)
</script>

<style scoped>
.base-input-wrapper {
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-2);
}

.base-input__label {
  font-size: var(--ds-text-body-sm);
  font-weight: var(--ds-weight-semibold);
  color: var(--ds-ink-2);
}

.base-input__required {
  color: var(--ds-red);
  margin-left: var(--ds-space-1);
}

.base-input__container {
  display: flex;
  align-items: center;
  min-height: var(--ds-input-height);
  background-color: var(--ds-input-bg);
  border: 1px solid var(--ds-input-border);
  border-radius: var(--ds-input-radius);
  transition:
    border-color var(--ds-control-transition),
    box-shadow var(--ds-control-transition),
    background-color var(--ds-control-transition);
}

.base-input__container:hover:not(.base-input__container--focused):not(.base-input__container--disabled):not(.base-input__container--readonly) {
  border-color: var(--ds-input-border-hover);
}

.base-input__container--focused {
  border-color: var(--ds-input-focus-border);
  box-shadow: var(--ds-input-focus-ring);
}

.base-input-wrapper--error .base-input__container {
  border-color: var(--ds-input-error-border);
}

.base-input-wrapper--error .base-input__container--focused {
  box-shadow: var(--ds-input-error-ring);
}

.base-input__container--disabled {
  color: var(--ds-input-disabled-fg);
  background: var(--ds-input-disabled-bg);
  border-color: var(--ds-btn-disabled-border);
  cursor: not-allowed;
}

.base-input__container--disabled .base-input__prefix,
.base-input__container--disabled .base-input__suffix {
  color: var(--ds-input-disabled-fg);
}

.base-input__container--readonly {
  background: var(--ds-input-readonly-bg);
}

.base-input {
  flex: 1;
  min-width: 0;
  height: calc(var(--ds-input-height) - 2px);
  padding: 0 var(--ds-input-padding-x);
  border: none;
  background: transparent;
  font-family: var(--ds-font-sans);
  font-size: var(--ds-text-body-sm);
  color: var(--ds-ink);
  outline: none;
}

.base-input::placeholder {
  color: var(--ds-placeholder);
}

.base-input:disabled {
  color: var(--ds-input-disabled-fg);
  cursor: not-allowed;
}

.base-input:read-only {
  cursor: default;
}

.base-input__prefix,
.base-input__suffix {
  display: flex;
  align-items: center;
  color: var(--ds-muted);
}

.base-input__prefix {
  padding-left: var(--ds-input-padding-x);
}

.base-input__suffix {
  padding-right: var(--ds-input-padding-x);
}

.base-input__error {
  margin: 0;
  font-size: var(--ds-text-caption);
  color: var(--ds-red);
  line-height: 1.45;
}

.base-input__hint {
  margin: 0;
  font-size: var(--ds-text-caption);
  color: var(--ds-muted);
  line-height: 1.45;
}
</style>
