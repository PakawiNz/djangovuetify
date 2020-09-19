import Vue from 'vue'

import axios from 'axios'
import lodash from 'lodash'

Vue.prototype.$ajax = axios
axios.defaults.xsrfCookieName = 'csrftoken'
axios.defaults.xsrfHeaderName = 'X-CSRFToken'

axios.upload = function (url, data) {
  let formData = new FormData()
  lodash.forEach(data, (value, key) => {
    formData.append(key, value)
  })
  return axios.post(url, formData)
}
