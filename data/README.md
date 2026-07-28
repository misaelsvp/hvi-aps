# Data

The census aggregates, the sector shapefile, the contiguity matrices and the state maps are too
large for version control. They are hosted on Amazon S3, in the bucket
`previsao-de-demanda-na-aps`, region `sa-east-1`. The scripts in `code/` expect them under this
directory, in the paths shown below.

| Object | Size | Local path expected by the scripts |
|---|---|---|
| `data/shapefiles/brazil_census_sectors_2022.shp` (with `.dbf`, `.shx`, `.prj`, `.cpg`) | 1.25 GB + 988 MB | `data/shapefiles/` |
| `data/census_2000_2010_2022_normalized_indices.csv` | 1.24 GB | `data/` |
| `data/adjacency_matrices/all_matrices.pkl` | 1.44 GB | `data/adjacency_matrices/` |
| `data/adjacency_matrices/processing_buffer.pkl` | 176 MB | `data/adjacency_matrices/` |
| `data/state_maps/state_map_*.html` (27 files) | 8 MB to 167 MB each | `data/state_maps/` |
| `data/sector_cluster/sector_cluster_by_uf.csv` | 12.6 MB | `data/` |

To retrieve a single object:

```
aws s3 cp s3://previsao-de-demanda-na-aps/data/sector_cluster/sector_cluster_by_uf.csv . --region sa-east-1
```

To retrieve the shapefile and the state maps:

```
aws s3 cp s3://previsao-de-demanda-na-aps/data/shapefiles/ shapefiles/ --recursive --region sa-east-1
aws s3 cp s3://previsao-de-demanda-na-aps/data/state_maps/ state_maps/ --recursive --region sa-east-1
```

`census_2000_2010_2022_normalized_indices.csv` carries the raw census variables together with
z-scored copies of each one, and three dimension columns named `Capital_Humano`, `Infra_Urbana`
and `Vul_Saude` plus an `Indice` column. It comes from an earlier stage of the work, when the
index had three dimensions and variables were standardised rather than ranked. The four-dimension
percentile-rank index described in the manuscript is the one produced by `code/build_hvi.py`, and
it reads the IBGE aggregates by sector directly, not this file.

The IBGE aggregates by census sector for the 2022 Census are published at
https://www.ibge.gov.br/estatisticas/sociais/trabalho/22827-censo-demografico-2022.html
