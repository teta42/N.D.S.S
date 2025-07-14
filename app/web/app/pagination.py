from rest_framework.pagination import PageNumberPagination, LimitOffsetPagination

class CommentPagination(PageNumberPagination):
    page_size = 1
    page_size_query_param = 'page_size'
    max_page_size = 10
    

class SearchNotePagination(LimitOffsetPagination):
    default_limit = 10
    max_limit = 100