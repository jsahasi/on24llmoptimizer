BRAND_DEFINITIONS = {
    "on24": {
        "display_name": "ON24",
        "aliases": ["on24", "on 24", "on24.com"],
        "target_domains": ["www.on24.com", "on24.com"],
        "exclude_domains": ["event.on24.com"],
        "description": "B2B webinar and virtual event platform",
    },
    "goldcast": {
        "display_name": "Goldcast",
        "aliases": ["goldcast", "goldcast.io", "gold cast"],
        "target_domains": ["www.goldcast.io", "goldcast.io"],
        "exclude_domains": [],
        "description": "B2B event marketing platform",
    },
    "zoom": {
        "display_name": "Zoom (Webinars/Events)",
        "aliases": ["zoom webinar", "zoom webinars", "zoom events"],
        "target_domains": ["zoom.us", "www.zoom.us"],
        "exclude_domains": [],
        "description": "Zoom Webinars and Zoom Events (virtual events only)",
        "context_filter": "webinar|virtual event|event platform|webcast",
        "exclude_context": "zoom meetings|video conferencing|zoom phone|zoom rooms",
    },
}
