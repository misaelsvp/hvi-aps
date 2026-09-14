# Data

The Amazon S3 bucket that previously hosted the census aggregates, the sector shapefile, the
contiguity matrices and the state maps is no longer reachable. Anonymous requests return
`403 AllAccessDisabled` and authenticated requests return `InvalidAccessKeyId`, which indicates the
account itself is gone rather than public access having been switched off. The two derived tables
that the scripts actually consume are therefore kept in this repository, gzipped.

| File | Rows | Content |
|---|---|---|
| `hvi_by_sector.csv.gz` | 458,772 | one row per 2022 census tract: dimension scores, index, resident population |
| `sector_cluster.csv.gz` | 451,383 | tract to cluster assignment, with state and municipality codes |

Decompress before running the scripts:

```
gzip -dk data/hvi_by_sector.csv.gz data/sector_cluster.csv.gz
```

`hvi_by_sector.csv.gz` carries the dimension columns of an earlier specification of the index,
which had three dimensions standardised to zero mean and unit variance. The four-dimension
percentile-rank index described in the manuscript is the one produced by `code/build_hvi.py`, which
reads the IBGE aggregates by census tract directly. Running that script replaces this file.

The IBGE aggregates by census tract for the 2022 Census, and the corresponding tract boundaries,
are published by the institute at
https://www.ibge.gov.br/estatisticas/sociais/trabalho/22827-censo-demografico-2022.html

`code/build_contiguity.py` and the Moran's I section of `code/validate.py` need the tract
boundaries, which are too large for version control and are not redistributed here. Download them
from IBGE at the address above.
