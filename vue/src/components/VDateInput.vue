<template>
  <v-dialog ref="dialog" v-model="modal" width="290px">
    <template v-slot:activator="{ on }">
      <v-text-field :value="value" @input="typeDate" v-bind="{ ...$attrs, ...$props }" @click:prepend="modal = true" prepend-icon="mdi-calendar"></v-text-field>
      <div v-on="on" />
    </template>
    <v-date-picker :value="value" @input="selectDate" />
  </v-dialog>
</template>
<script>
export default {
  props: ['label', 'value'],
  data: () => ({
    modal: false,
  }),
  methods: {
    typeDate(event) {
      this.$emit('input', event)
    },
    selectDate(event) {
      this.$emit('input', event)
      this.modal = false
    },
    clickClearDate() {
      this.$emit('input', null)
      this.modal = false
    },
  },
}
</script>
