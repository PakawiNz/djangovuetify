module.exports = {
  root: true,
  env: {
    node: true,
  },
  extends: ['standard', 'plugin:vue/recommended'],
  rules: {
    'comma-dangle': 'off',
    'space-before-function-paren': 'off',
    'vue/max-attributes-per-line': 'off',
    'no-console': process.env.NODE_ENV === 'production' ? 'error' : 'off',
    'no-debugger': process.env.NODE_ENV === 'production' ? 'error' : 'off',
  },
  parserOptions: {
    parser: 'babel-eslint',
  },
}
