"""Figures: served as images, embedded in lessons, listed for review, exported."""

from __future__ import annotations

from httpx import AsyncClient


async def test_a_figure_is_served_as_an_image(study_client: AsyncClient) -> None:
    response = await study_client.get("/api/figures/fig-one.svg")
    assert response.status_code == 200, response.text
    assert response.headers["content-type"].startswith("image/svg+xml")
    assert response.text.lstrip().startswith("<svg")
    assert (await study_client.get("/api/figures/nope.svg")).status_code == 404
    # A lesson key is not a figure key.
    assert (await study_client.get("/api/figures/lesson-one.svg")).status_code == 404


async def test_a_lesson_carries_its_figures(study_client: AsyncClient) -> None:
    lesson = (await study_client.get("/api/lessons/lesson-one")).json()
    assert [figure["key"] for figure in lesson["figures"]] == ["fig-one"]
    figure = lesson["figures"][0]
    assert figure["url"] == "/api/figures/fig-one.svg"
    assert figure["title"] == "Figure one" and figure["alt"] == "A box labelled Figure one"
    assert figure["caption_md"].startswith("A **box**")
    assert [o["code"] for o in figure["objectives"]] == ["1.1"]
    assert "(figure:fig-one)" in lesson["body_md"]
    # A lesson without figures says so.
    assert (await study_client.get("/api/lessons/lesson-two")).json()["figures"] == []


async def test_figures_are_content_items_that_export_and_reimport(
    study_client: AsyncClient,
) -> None:
    listed = (await study_client.get("/api/content/items", params={"kind": "figure"})).json()
    assert [item["key"] for item in listed["items"]] == ["fig-one"]
    assert listed["items"][0]["preview"] == "Figure one"

    exported = (await study_client.get("/api/content/export/mini-test-pack")).json()
    figures = exported["figures"]
    assert len(figures) == 1 and figures[0]["svg"].lstrip().startswith("<svg")
    assert figures[0]["file"] is None
    again = await study_client.post("/api/content/import", json={"pack": exported, "dry_run": True})
    assert again.json()["counts"] == {"created": 0, "updated": 0, "unchanged": 17, "retired": 0}
