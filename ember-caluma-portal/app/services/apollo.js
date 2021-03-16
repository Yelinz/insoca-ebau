import { setContext } from "@apollo/client/link/context";
import { onError } from "@apollo/client/link/error";
import { inject as service } from "@ember/service";
import ApolloService from "ember-apollo-client/services/apollo";
import CalumaApolloServiceMixin from "ember-caluma/mixins/caluma-apollo-service-mixin";

export default class CustomApolloService extends ApolloService.extend(
  CalumaApolloServiceMixin
) {
  @service session;

  link(...args) {
    const httpLink = super.link(...args);

    const middleware = setContext(async (_, context) => ({
      ...context,
      headers: { ...context.headers, ...this.session.authHeaders },
    }));

    const afterware = onError((error) => {
      if (error.networkError && error.networkError.statusCode === 401) {
        this.session.handleUnauthorized();
      }
    });

    return middleware.concat(afterware).concat(httpLink);
  }
}
