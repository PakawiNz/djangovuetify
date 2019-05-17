module.exports = {
  publicPath: '/static/',
  devServer: {
    disableHostCheck: true,
    proxy: {
      '^/(api|admin|static|media|ws)': {
        target: 'http://localhost:8088',
      },
    },
  },
}
