# Decisions

Below are the selected defaults the agent must implement and record (with numbers) in `DECISIONS.md`:

1. **STAC & extensions**: 1A — STAC 1.0.0 with proj, raster, processing (latest patch).  
2. **Primary COG key**: 2C — Analyzer-defined key; publisher marks `roles=["data","primary"]`.  
3. **COG toolchain**: 3B — rio-cogeo (optimized overviews; small, focused dep).  
4. **PMTiles**: 4A — tippecanoe → PMTiles.  
5. **CRS/validity**: 5C — reproject only; error & skip invalid geometries (summarize).  
6. **Item geometry policy**: 6C — always include geometry/bbox; update examples accordingly.  
7. **Idempotency/paths**: 7D — everything under `jobs/<job_id>/`; map can be repointed to the new Collection path.  
8. **S3 layout**: 8A — fixed prefixes as in config.  
9. **Bucket/security**: 9B — private bucket; SSE-S3; exposure via TiTiler/CloudFront later.  
10. **CI matrix**: 10B — Ubuntu; Python 3.11 & 3.12.  
11. **Coverage**: 11B — 95% global; 100% on core.  
12. **S3 tests**: A — botocore Stubber.  
13. **GitHub auth**: 13A — GITHUB_TOKEN.  
14. **CI red**: 14A — abort immediately (pre-commit should catch most).  
15. **CLI UX**: 15D — “pythonic & useful for debugging”: JSON logs by default with `--verbose` escalating detail; clear exceptions; progressive status lines for long ops.  
16. **TimeProvider discovery**: A — `--time-provider module:callable`.  
17. **ULIDs**: 17A — fresh ULIDs each run.  
18. **Hosting & CORS**: 18A — same origin, relative STAC paths.  
19. **Map ↔ TiTiler flow**: Collection points to PMTiles; features include Item URL/path (resolved via config `base_url` if provided); map fetches Item JSON, reads primary COG, builds TiTiler TileJSON URL from config base, and renders.  
20. **media_type/roles**: 20B — publisher validates/normalizes (e.g., COG mediatype on `.tif`).  
21. **HREF enforcement**: All HREFs are library-derived; hard fail if any non-COG absolute/protocol link appears.  
22. **External binaries**: 22A — minimal wrappers; fail if missing; document install.  
23. **OS targets**: 23A — Linux-first; best-effort macOS; no Windows.  
24. **Scale/parallelism**: 24C — no parallelism in v1; document limits/roadmap.  
25. **Config & secrets**: 25A — JSON config; AWS creds from env/SDK.  
26. **STAC validation rigor**: 26B — validate examples in CI.  
27. **Release artifacts**: 27B — tags only.  
28. **Badges**: 28A — shields.io.  
29. **Log format**: 29B — JSON logs (machine-friendly).  
30. **Dep policy**: 30A — pin exact versions in `requirements*.txt`.  
31. **Partial publish**: 31B — leave partial; write manifest with failure status; exit non-zero.  
32. **Leaflet UI scope**: 32A — feature picker + date slider + raster toggle.  
33. **Licensing in STAC**: 33B — toolkit MIT only; data license handling out of scope v1.  
34. **Scale (now)**: 34A — ≤1k features; a few GB rasters.  
35. **Demo analyzer**: 35A — ship a tiny demo analyzer producing a small COG (e.g., clip/reproject).  

---

**Note**: If future choices conflict, favor:  
1. HREF correctness  
2. S3-default publishing  
3. CI gate integrity  
4. TiTiler primary asset discoverability
