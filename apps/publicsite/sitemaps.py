from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from apps.branches.selectors import public_branches
from apps.cms.selectors import published_items


class PublicSitemap(Sitemap):
    i18n = True
    alternates = True
    x_default = True


class PagesSitemap(PublicSitemap):
    def items(self):
        return [
            "home",
            "public-about",
            "public-programs",
            "public-branches",
            "public-events",
            "volunteer-apply",
            "public-contact",
            "public-privacy",
        ]

    def location(self, item):
        return reverse(item)


class ContentSitemap(PublicSitemap):
    def items(self):
        return published_items().filter(type__in=["PROGRAM", "EVENT"])

    def location(self, item):
        route = (
            "public-program-detail" if item.type == "PROGRAM" else "public-event-detail"
        )
        return reverse(route, kwargs={"slug": item.published_snapshot["meta"]["slug"]})

    def lastmod(self, item):
        return item.published_at


class BranchesSitemap(PublicSitemap):
    def items(self):
        return public_branches()

    def location(self, item):
        return reverse("public-branch-detail", kwargs={"code": item.code})

    def lastmod(self, item):
        return item.updated_at


SITEMAPS = {
    "pages": PagesSitemap,
    "content": ContentSitemap,
    "branches": BranchesSitemap,
}
