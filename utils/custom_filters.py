from rest_framework.filters import SearchFilter


class CustomSearchFilter(SearchFilter):
    def get_search_terms(self, request):
        """
        Overriding to treat the entire search query as a single term.
        The default SearchFilter splits the query by spaces or commas.
        """
        params = request.query_params.get(self.search_param, "")
        params = params.replace("\x00", "")  # strip null characters
        # We don't replace commas with spaces here, and we don't split.
        # Just return the single string as a list with one item.
        return [params.strip()] if params.strip() else []
