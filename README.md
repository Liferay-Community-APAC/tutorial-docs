# Tutorial docs

Step-by-step Liferay DXP tutorials from Liferay Community APAC that are published as web pages rather than kept in
a code repository, at `https://liferay-community-apac.github.io/tutorial-docs/<tutorial>/`. The main site's
[Tutorials & Tools](https://liferay-community-apac.github.io/tutorials/) page lists them next to the tutorials that
live in their own repositories.

The tutorials are Markdown pages in `docs/`, built with Jekyll and published by the shared Liferay Community APAC
workflow whenever `docs/` changes on `main`. Each tutorial has its own folder, with its own sidebar, breadcrumbs and
previous and next links, and shares the main site's header, footer, styles and search.

A tutorial whose readers need working code, such as a Liferay Workspace or client extensions, belongs in a
repository of its own instead, like the
[EC2 tutorial](https://github.com/Liferay-Community-APAC/lfrgs-sh-aws-ec2-tutorial).

## What's here

| Path | What it is |
| --- | --- |
| `docs/<tutorial>/` | One folder per tutorial. Its `index.md` is the tutorial's home page. |
| `TUTORIAL_TEMPLATE/` | A starting point for a new tutorial's folder. |
| `docs/example-tutorial/` | A placeholder. Delete it when the first real tutorial is added. |
| `docs/_layouts/default.html` | The page layout. The sidebar and breadcrumbs cover the current tutorial only. |
| `docs/index.md` | Forwards `/tutorial-docs/` to the main site's Tutorials & Tools page. |
| `.github/workflows/pages.yml` | Publishes the docs with the shared workflow whenever `docs/` changes on `main`. |

## Add a tutorial

1. **Copy `TUTORIAL_TEMPLATE/` to `docs/<tutorial>/`**, where `<tutorial>` is the tutorial's name in lowercase with
   dashes, for example `docs/headless-commerce-storefront/`. The folder name becomes the tutorial's address.
2. **Edit `docs/<tutorial>/index.md`**: the tutorial's name (`title`), a one-sentence `description`, the
   `footer_note` (its licence line, or remove it), and the four sections: **What You'll Build**,
   **Before You Start**, **Chapters** and **Status**.
3. **Write the chapters** in `docs/<tutorial>/chapters/`, one Markdown page each, ending with a **Check** that
   readers can confirm before going on. Each page starts with front matter:

    ```yaml
    ---
    title: 1. Set Up         # the page's name in the sidebar
    parent: Chapters         # the section it belongs to (leave out for a section or top page)
    nav_order: 1             # its position, lower first
    ---
    ```

    Pages can use a table of contents (`1. TOC` then `{:toc}` on the next line), callouts
    (`{: .note }`, `{: .tip }`, `{: .important }` or `{: .warning }` on the line before a paragraph),
    and screenshots (`{: .screenshot }` after an image). Put images in the tutorial's folder. Code blocks get a
    **Copy** button.
4. **Add the tutorial to the main site**: add an entry to `data/apps.json` in
   [liferay-community-apac.github.io](https://github.com/Liferay-Community-APAC/liferay-community-apac.github.io)
   with `"category": "tutorials"` and:

    ```json
    "docs": "tutorial-docs/<tutorial>/",
    "search": "tutorial-docs/pagefind/",
    "sitemap": "tutorial-docs/sitemap.xml"
    ```

    That lists the tutorial on the Tutorials & Tools pages in every language, includes it in the site search, and
    tells search engines about it.
5. **Open a pull request.**

## Preview locally

Set `main_site: https://liferay-community-apac.github.io` in `docs/_config.yml` (don't commit it), then:

```bash
cd docs && jekyll serve --baseurl /tutorial-docs
```

## Publishing

In **Settings → Pages**, **Source** must be **GitHub Actions**.

Keep this repository's name as it is. GitHub publishes a repository's pages at `/<repository name>/`, and the
main site already uses `/tutorials/`, so a repository named `tutorials` would take that address over.
