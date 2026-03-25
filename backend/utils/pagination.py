"""
Custom pagination classes for MegaStore API.

Provides standardized paginated response formats across all
API endpoints, with configurable page sizes and metadata.
"""

from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class StandardResultsPagination(PageNumberPagination):
    """
    Standard pagination for most API endpoints.

    Returns paginated results with metadata including total count,
    page links, and current page info. Default page size is 20,
    configurable up to 100 via the `page_size` query parameter.
    """

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100
    page_query_param = "page"

    def get_paginated_response(self, data):
        return Response(
            {
                "count": self.page.paginator.count,
                "total_pages": self.page.paginator.num_pages,
                "current_page": self.page.number,
                "page_size": self.get_page_size(self.request),
                "next": self.get_next_link(),
                "previous": self.get_previous_link(),
                "results": data,
            }
        )

    def get_paginated_response_schema(self, schema):
        return {
            "type": "object",
            "required": ["count", "results"],
            "properties": {
                "count": {
                    "type": "integer",
                    "description": "Total number of results across all pages.",
                },
                "total_pages": {
                    "type": "integer",
                    "description": "Total number of pages.",
                },
                "current_page": {
                    "type": "integer",
                    "description": "Current page number.",
                },
                "page_size": {
                    "type": "integer",
                    "description": "Number of results per page.",
                },
                "next": {
                    "type": "string",
                    "nullable": True,
                    "format": "uri",
                    "description": "URL to the next page of results.",
                },
                "previous": {
                    "type": "string",
                    "nullable": True,
                    "format": "uri",
                    "description": "URL to the previous page of results.",
                },
                "results": schema,
            },
        }


class SmallResultsPagination(PageNumberPagination):
    """
    Smaller page size pagination for lightweight endpoints.

    Used for endpoints like reviews, addresses, and notifications
    where smaller result sets are typical.
    """

    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 50


class LargeResultsPagination(PageNumberPagination):
    """
    Larger page size pagination for admin and export endpoints.

    Used in admin dashboards and data export where more results
    per page reduces the number of API calls needed.
    """

    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 200
