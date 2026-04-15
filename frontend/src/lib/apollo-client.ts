import { ApolloClient, HttpLink, InMemoryCache } from "@apollo/client";
import { GRAPHQL_URL } from "@/lib/config";

export function makeApolloClient() {
  return new ApolloClient({
    link: new HttpLink({ uri: GRAPHQL_URL }),
    cache: new InMemoryCache(),
  });
}
