import CamacInputComponent from 'citizen-portal/components/camac-input/component'
import { computed } from '@ember/object'
import { reads } from '@ember/object/computed'
import { inject as service } from '@ember/service'
import { task } from 'ember-concurrency'
import UIkit from 'uikit'
import fetch from 'fetch'
import Ember from 'ember'
import download from 'downloadjs'

const { testing } = Ember

const ALLOWED_MIME_TYPES = ['application/pdf', 'image/png', 'image/jpeg']
const MAX_FILE_SIZE = 12 * 1024 * 1024

export default CamacInputComponent.extend({
  ajax: service(),
  store: service(),
  session: service(),

  token: reads('session.data.authenticated.access_token'),

  headers: computed('token', function() {
    return {
      Authorization: `Bearer ${this.token}`
    }
  }),

  classNameBindings: ['question.hidden:uk-hidden'],
  classNames: ['uk-margin-remove', 'uk-animation-fade'],

  mimeTypes: ALLOWED_MIME_TYPES.join(','),

  download: task(function*() {
    try {
      let question = yield this.question

      if (!question.get('model.path')) {
        return
      }

      let response = yield fetch(question.get('model.path'), {
        mode: 'cors',
        headers: this.headers
      })

      let file = yield response.blob()

      if (!testing) {
        download(file, question.get('model.name'), file.type)
      }

      UIkit.notification('Datei wurde erfolgreich heruntergeladen', {
        status: 'success'
      })
    } catch (e) {
      UIkit.notification(
        'Hoppla, beim Herunterladen der Datei ist etwas schief gelaufen. Bitte versuchen Sie es nochmals',
        { status: 'danger' }
      )
    }
  }),

  upload: task(function*(files) {
    if (this.readonly) {
      return
    }

    try {
      let file = files.item(0)

      if (file.size > MAX_FILE_SIZE) {
        UIkit.notification(
          `Die Datei darf nicht grösser als ${MAX_FILE_SIZE /
            1024 /
            1024}MB sein.`,
          { status: 'danger' }
        )

        return
      }

      if (!ALLOWED_MIME_TYPES.includes(file.type)) {
        UIkit.notification(
          'Es können nur PDF, JPEG oder PNG Dateien hochgeladen werden.',
          { status: 'danger' }
        )

        return
      }

      let question = yield this.question

      let filename = `${question.get('name')}.${file.name.split('.').pop()}`

      let formData = new FormData()
      formData.append('instance', question.get('model.instance.id'))
      formData.append('path', file, filename)

      let response = yield this.ajax.request('/api/v1/attachments', {
        method: 'POST',
        cache: false,
        contentType: false,
        processData: false,
        data: formData,
        headers: {
          Accept: 'application/vnd.api+json'
        }
      })

      this.store.pushPayload(response)

      question.set(
        'model',
        this.store.peekRecord('attachment', response.data.id)
      )

      UIkit.notification('Die Datei wurde erfolgreich hochgeladen', {
        status: 'success'
      })
    } catch (e) {
      UIkit.notification(
        'Hoppla, beim Hochladen der Datei ist etwas schief gelaufen. Bitte versuchen Sie es nochmals',
        { status: 'danger' }
      )
    }
  }),

  actions: {
    triggerUpload() {
      this.element.querySelector('input[type=file').click()
    }
  }
})
