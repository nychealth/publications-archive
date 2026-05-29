# Publications Archive
This repository contains an archive of NYC Health Department Publications.

## Notable files
It runs off of two important data files:
- pdf.json is scraped from the subpages of the [Health Department's Publications Page](https://www.nyc.gov/site/doh/data/data-publications/periodic-publications.page), including the Publications Archive. This was scraped March 2026.
- peer.csv (and its variants) is the result of a search of PubMed for manuscripts that include a listed affiliation to the NYC Health Department, dating back to 2010, through 2026. This was last updated 2026-05-29.

## Scraper functionality
The scripts in `/scraper` search for publications with any of these affiliations:
- New York City Department of Health and Mental Hygiene
- NYC Department of Health and Mental Hygiene
- NYC DOHMH
- NYCDOHMH

`pubmed_search.py` looks for publications from January 1, 2026, to the present. It creates `pubmed_results.csv`, appends new entries into `peer.csv`, and deduplicates by PMID.

`pubmed_search_historical.py` looks for publications from a `startyear` to an `endyear`.

Both scripts create a CSV file with these columns:
- **PMID** - PubMed ID
- **Title** - Article title
- **Authors** - List of authors
- **Year** - Publication year
- **Date** - Full publication date
- **Link** - PubMed URL
- **Journal** - Journal name
- **DOI** - Digital Object Identifier
- **Keywords** - Article keywords

### Setup Instructions

#### 1. Configure Email

Edit `pubmed_search.py` and change this line (around line 14):
```python
Entrez.email = "your.email@example.com"  # Change this to your email
```

Replace with your actual email address. NCBI requires this for API access.

#### 2. Enable GitHub Actions

1. Go to your repository's **Settings** → **Actions** → **General**
2. Under "Workflow permissions", select **"Read and write permissions"**
3. Click **Save**

This allows the workflow to commit the Excel file back to the repository.

#### 3. Test It

1. Go to the **Actions** tab in your repository
2. Click on "PubMed Search - NYC DOHMH" workflow
3. Click **"Run workflow"** → **"Run workflow"** (green button)
4. Wait a few minutes for it to complete
5. Check your repository - you should see a new `pubmed_results.csv` file!

### Schedule

The search runs automatically **every Monday at 9 AM UTC** (4 AM EST / 5 AM EDT).

It searches for all publications from January 1, 2026, to the present and adds any new results to the existing CSV file.

To change the schedule, edit `.github/workflows/pubmed-search.yml` and modify the cron expression:

```yaml
schedule:
  - cron: '0 9 * * 1'  # Monday at 9 AM UTC
```

Cron format: `minute hour day-of-month month day-of-week`

Examples:
- `0 9 * * 1` - Every Monday at 9 AM UTC
- `0 9 * * *` - Every day at 9 AM UTC
- `0 9 1 * *` - First day of each month at 9 AM UTC
- `0 9 1,15 * *` - 1st and 15th of each month at 9 AM UTC

### Accessing Results

After each run, the `pubmed_results.csv` file in your repository will be updated.

To download it:
1. Click on `pubmed_results.csv` in your repository
2. Click the "Download" button (or "Raw" to download directly)

### 🛠️ Customization

#### Change the date range

Edit `pubmed_search.py`, line 16:
```python
id_list = search_pubmed(query, start_date_str="2026/01/01")  # Change the start date
```

To change the start date, modify the `start_date_str` parameter.

#### Change the search query

Edit the `query` variable in `pubmed_search.py` (around line 102).

#### Add email notifications

To receive emails when the workflow runs, add this step to `.github/workflows/pubmed-search.yml`:

```yaml
    - name: Send email
      uses: dawidd6/action-send-mail@v3
      with:
        server_address: smtp.gmail.com
        server_port: 465
        username: ${{ secrets.EMAIL_USERNAME }}
        password: ${{ secrets.EMAIL_PASSWORD }}
        subject: PubMed Search Complete - ${{ steps.date.outputs.date }}
        to: your.email@example.com
        from: GitHub Actions
        body: New PubMed results are available!
        attachments: pubmed_results.csv
```

You'll need to add email credentials to your repository secrets.

### Notes

- The script is polite to NCBI servers (includes delays between requests)
- Results are accumulated over time, with new publications added weekly
- Empty CSV file is created if no results are found initially
- The script handles various date formats and missing data gracefully

### Troubleshooting

**Workflow fails with permission error:**
- Make sure you enabled "Read and write permissions" in repository settings

**No results found:**
- Check if there are actually publications in the last 30 days
- Verify the affiliation search terms are correct

**Email not set:**
- Don't forget to update `Entrez.email` in the Python script


### Historical Search

For one-time searches of historical data, use `pubmed_search_historical.py`:

```bash
python3 pubmed_search_historical.py <start_year> <end_year>
```

Example:
```bash
python3 pubmed_search_historical.py 2020 2025
```

This will search for publications from January 1, 2020, to December 31, 2025, and create `historical_results-2020-2025.csv`.