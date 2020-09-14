<template>
  <v-app>
    <v-app-bar app dark>
      <v-toolbar-title>Watchara Corp.</v-toolbar-title>
      <v-spacer></v-spacer>
      <v-btn rounded icon>
        <v-icon>mdi-magnify</v-icon>
      </v-btn>
      <v-btn rounded icon @click="$refs.fileSelector.click()">
        <v-icon>mdi-upload</v-icon>
      </v-btn>
    </v-app-bar>
    <v-main>
      <v-container fluid>
        <v-row align="baseline" justify="center">
          <v-col class="text-center">
            <v-data-table :headers="headers" :items="items" :sort-by="['calories', 'fat']" :sort-desc="[false, true]" class="elevation-1" multi-sort />
          </v-col>
        </v-row>
        <v-spacer />
      </v-container>
    </v-main>
    <v-footer app> </v-footer>
    <div style="display: none;">
      <input type="file" multiple ref="fileSelector" accept="application/pdf" @input="fileSelected" />
    </div>
  </v-app>
</template>

<script>
export default {
  props: {
    source: String,
  },
  data: () => ({
    drawer: null,
    uploading: [],
    headers: [
      {
        text: 'Dessert (100g serving)',
        align: 'start',
        sortable: false,
        value: 'name',
      },
      { text: 'Calories', value: 'calories' },
      { text: 'Fat (g)', value: 'fat' },
      { text: 'Carbs (g)', value: 'carbs' },
      { text: 'Protein (g)', value: 'protein' },
      { text: 'Iron (%)', value: 'iron' },
    ],
    desserts: [
      {
        name: 'Frozen Yogurt',
        calories: 200,
        fat: 6.0,
        carbs: 24,
        protein: 4.0,
        iron: '1%',
      },
      {
        name: 'Ice cream sandwich',
        calories: 200,
        fat: 9.0,
        carbs: 37,
        protein: 4.3,
        iron: '1%',
      },
      {
        name: 'Eclair',
        calories: 300,
        fat: 16.0,
        carbs: 23,
        protein: 6.0,
        iron: '7%',
      },
      {
        name: 'Cupcake',
        calories: 300,
        fat: 3.7,
        carbs: 67,
        protein: 4.3,
        iron: '8%',
      },
      {
        name: 'Gingerbread',
        calories: 400,
        fat: 16.0,
        carbs: 49,
        protein: 3.9,
        iron: '16%',
      },
      {
        name: 'Jelly bean',
        calories: 400,
        fat: 0.0,
        carbs: 94,
        protein: 0.0,
        iron: '0%',
      },
      {
        name: 'Lollipop',
        calories: 400,
        fat: 0.2,
        carbs: 98,
        protein: 0,
        iron: '2%',
      },
      {
        name: 'Honeycomb',
        calories: 400,
        fat: 3.2,
        carbs: 87,
        protein: 6.5,
        iron: '45%',
      },
      {
        name: 'Donut',
        calories: 500,
        fat: 25.0,
        carbs: 51,
        protein: 4.9,
        iron: '22%',
      },
      {
        name: 'KitKat',
        calories: 500,
        fat: 26.0,
        carbs: 65,
        protein: 7,
        iron: '6%',
      },
      {
        name: 'Donut',
        calories: 500,
        fat: 25.0,
        carbs: 51,
        protein: 4.9,
        iron: '22%',
      },
      {
        name: 'KitKat',
        calories: 500,
        fat: 26.0,
        carbs: 65,
        protein: 7,
        iron: '6%',
      },
      {
        name: 'Donut',
        calories: 500,
        fat: 25.0,
        carbs: 51,
        protein: 4.9,
        iron: '22%',
      },
      {
        name: 'KitKat',
        calories: 500,
        fat: 26.0,
        carbs: 65,
        protein: 7,
        iron: '6%',
      },
      {
        name: 'Donut',
        calories: 500,
        fat: 25.0,
        carbs: 51,
        protein: 4.9,
        iron: '22%',
      },
      {
        name: 'KitKat',
        calories: 500,
        fat: 26.0,
        carbs: 65,
        protein: 7,
        iron: '6%',
      },
    ],
  }),
  computed: {
    items() {
      return [
        ...this.uploading.map(file => ({
          name: file.name,
          calories: file.size,
          fat: 0,
          carbs: 0,
          protein: 0,
          iron: 'X',
        })),
        ...this.desserts,
      ]
    },
  },
  methods: {
    fileSelected(event) {
      this.uploading = [this.uploading, ...this.$refs.fileSelector.files]
    },
  },
}
</script>

<style lang="scss"></style>
