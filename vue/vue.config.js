module.exports = {
  publicPath: process.env.NODE_ENV === 'production' ? '/static/' : '/',
  devServer: {
    disableHostCheck: true,
    port: 8001,
    proxy: {
      '^/(api|admin|static|media|ws)': {
        target: 'http://localhost:8000',
      },
    },
  },
}
