module.exports = {
  publicPath: process.env.NODE_ENV === 'production' ? '/static/' : '/',
  devServer: {
    disableHostCheck: true,
    port: 8000,
    proxy: {
      '^/(api|admin|static|media|ws)': {
        target: 'http://localhost:8088',
      },
    },
  },
}
