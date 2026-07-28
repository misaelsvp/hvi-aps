# Health Vulnerability Index and territorial clustering for Primary Health Care

Supplementary material for the manuscript entitled "Health Vulnerability Index and territorial clustering for Primary Health Care planning: a census-data and spatial analysis approach in Brazil".

Primary Health Care in Brazil is organised around the Family Health Strategy, whose teams are assigned to defined geographic catchment areas. Planning those areas depends on knowing where health vulnerability concentrates, and the census sector is the finest unit at which that can be measured for the whole country. The 2022 Demographic Census has 458,772 sectors, which is a useful resolution for measurement and an unusable one for management.

The Health Vulnerability Index is computed for every sector from 2022 Census variables, over four dimensions: urban infrastructure, human capital, income and employment, and demographic vulnerability. Eighteen indicators feed those dimensions. Each indicator is converted to its national percentile rank, so that quantities with different units and different dispersions can be combined without choosing weights for them. A dimension score is the mean of the ranks of its indicators, and the index is the mean of the four dimension scores. Values run from 0 to 1 and higher means more vulnerable.

Sectors are then aggregated into planning units. A unit has to be spatially connected under queen contiguity, meaning that its sectors share at least one boundary point, and it must not hold more people than a single Family Health team is meant to cover, around 3,000 residents. Every sector starts as its own cluster. The distance between two adjacent sectors is the absolute difference between their index values; every contiguous pair is sorted by that distance and the pairs are merged in order, whenever the two clusters are still separate and their combined population stays within the reference. A disjoint-set structure keeps track of which sectors already belong together, which is what makes the sweep cheap enough to run over hundreds of thousands of sectors. Sectors that on their own already exceed the reference stay isolated, since no merge could keep them within it. A final pass gives clusters that ended up below half the reference one more attempt with a neighbour. The procedure runs state by state.

Interactive maps of the resulting clusters for every state are at http://ivs-cluster-na-aps.s3-website-sa-east-1.amazonaws.com/

| Dimension | Indicators |
|---|---|
| Urban infrastructure | inadequate water supply, inadequate sewage, no garbage collection, households without bathroom, overcrowded households |
| Human capital | illiteracy at 15 and over, illiteracy from 15 to 29, female-headed households without spouse, illiterate household heads, illiterate female household heads |
| Income and employment | low household-head income, adolescent household heads, substandard housing |
| Demographic vulnerability | population 65 and over, population 0 to 4, households headed by older adults, dependency ratio, premature mortality from 30 to 69 |

The IBGE variable codes behind each indicator are listed in the appendix of the manuscript and in `code/build_hvi.py`.

**Code.** `build_hvi.py` reads the 2022 Census aggregates by sector and writes the eighteen indicators, the four dimension scores and the index. `build_contiguity.py` reads the census sector shapefile and writes the queen contiguity neighbour lists, one set per state. `cluster_sectors.py` runs the aggregation described above and writes the sector to cluster assignment. `recover_sector_cluster.py` rebuilds that same assignment from the published state maps instead of recomputing it, by extracting the cluster polygons embedded in each HTML file and locating the centroid of every sector inside them; it is the route to take when the maps are the artifact at hand.

**Data.** The census aggregates, the shapefile, the contiguity matrices and the state maps are too large for version control and are hosted on Amazon S3. `data/README.md` lists every object with its size and the commands to retrieve it.

Requires Python 3.10 or later. `pip install -r code/requirements.txt`
