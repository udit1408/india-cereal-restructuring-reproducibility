# Zenodo Release Checklist

This repository is prepared for archiving through the Zenodo GitHub integration.

## What controls the Zenodo record

- `.zenodo.json` controls the metadata Zenodo uses when archiving a GitHub release.
- `CITATION.cff` is still useful because GitHub displays it as the repository citation suggestion.
- If both files are present, Zenodo uses `.zenodo.json` for GitHub-release archiving.

## One-time setup

1. Sign in to Zenodo and link the GitHub account that owns this repository.
2. In Zenodo, open the GitHub integration page, click `Sync now`, and enable:
   - `udit1408/india-cereal-restructuring-reproducibility`

## Before each archived release

1. Make sure `main` is pushed and clean.
2. If creator names, affiliations, keywords, or licensing changed, update:
   - `.zenodo.json`
   - `CITATION.cff`
3. If you want the citation file itself to show a release version on GitHub, update the version fields before tagging the release.

## Create the archival release

1. On GitHub, open the repository release page.
2. Create a new release with a semantic tag such as:
   - `v1.0.0`
3. Use the release title to match the tag or the intended public software version.
4. Publish the release.

Zenodo will ingest the GitHub release automatically after the repository has been enabled.

## After Zenodo finishes

Zenodo will create:

- a version-specific DOI for that exact release;
- a concept DOI that always resolves to the full version family.

Use the version DOI for exact reproducibility citations. Use the concept DOI when you want to refer to the evolving software record across releases.

## Updating after the first DOI

- Additional commits to GitHub do not create a new Zenodo DOI by themselves.
- Each new GitHub release creates a new Zenodo version DOI.
- The concept DOI remains stable across versions.
- Metadata-only edits on Zenodo do not change the DOI.

