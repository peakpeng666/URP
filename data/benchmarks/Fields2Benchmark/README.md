# Fields2Benchmark dataset

The Fields2Benhmark dataset is a collection of 350 agricultural fields in vector format manually selected to test agricultural coverage path planning algorithms.

The files in this dataset are organized into two folders:
- `imgs/`: contains the satellite images of the fields.
- `wkt/`: has the vector data of the fields.

A file with the same name in both folders corresponds to the same field. The first two letters in the name of the field indicate the country the field belongs to.


The fields have been extracted from the EuroCrops dataset --specifically from [the Netherlands](https://github.com/maja601/EuroCrops/wiki/Netherlands), [Estonia](https://github.com/maja601/EuroCrops/wiki/Estonia) and [Lithuania](https://github.com/maja601/EuroCrops/wiki/Lithuania ) --, transformed each field into its own file, and converted them to Well-Known text (wkt). The satellite images were also provided, and they were created using [the Mapping Toolbox from Matlab](https://es.mathworks.com/products/mapping.html).


## Funding

This dataset is provided as part of the project "Fields2Cover: Robust and efficient coverage paths for autonomous agricultural vehicles" (with project number ENPPS.LIFT.019.019 of the research programme Science PPP Fund for the top sectors which is (partly) financed by the Dutch Research Council (NWO).


```
  @article{Mier_Fields2Cover_An_open-source_2023,
    author={Mier, Gonzalo and Valente, João and de Bruin, Sytze},
    journal={IEEE Robotics and Automation Letters},
    title={Fields2Cover: An Open-Source Coverage Path Planning Library for Unmanned Agricultural Vehicles},
    year={2023},
    volume={8},
    number={4},
    pages={2166-2172},
    doi={10.1109/LRA.2023.3248439}
  }
```




## Other references and Licenses

These references have been extracted from [EuroCrops.wiki](https://github.com/maja601/EuroCrops-Wiki)

```
@Article{schneider2023eurocrops,
	title = {{EuroCrops}: {The} {Largest} {Harmonized} {Open} {Crop} {Dataset} {Across} the {European} {Union}},
	volume = {10},
	copyright = {All rights reserved},
	issn = {2052-4463},
	url = {https://doi.org/10.1038/s41597-023-02517-0},
	doi = {10.1038/s41597-023-02517-0},
	number = {1},
	journal = {Scientific Data},
	author = {Schneider, Maja and Schelte, Tobias and Schmitz, Felix and Körner, Marco},
	month = sep,
	year = {2023},
	pages = {612},
}
```

### The Netherlands

#### Data source
- [PDOK](https://service.pdok.nl/rvo/brpgewaspercelen/atom/v1_0/basisregistratie_gewaspercelen_brp.xml) (Data from 2009-2022)
- [Nationaal Georegister](https://www.nationaalgeoregister.nl/geonetwork/srv/dut/catalog.search;jsessionid=C5EF30EA1AB83278754FD85BC9C76BE4#/metadata/dd8e0fb8-0f09-40ba-a884-7e23c0680ae2) 
#### License
- PDOK Data
    - [CC0 1.0 Universal (CC0 1.0) Public Domain Dedication ](http://creativecommons.org/publicdomain/zero/1.0/deed.nl)
    - [no conditions to access and use](http://inspire.ec.europa.eu/metadata-codelist/ConditionsApplyingToAccessAndUse/noConditionsApply)
    - [no limitations to public access](https://inspire.ec.europa.eu/metadata-codelist/LimitationsOnPublicAccess/noLimitations)
- Nationaal Georegister Data: [Public Domain Mark 1.0](http://creativecommons.org/publicdomain/mark/1.0/deed.nl) (No Copyright)

### Estonia

#### Data Source
[INSPIRE GEOPORTAL](https://inspire-geoportal.ec.europa.eu/download_details.html?view=downloadDetails&resourceId=%2FINSPIRE-608e479c-616e-11e2-b563-52540004b857_20211215-093102%2Fservices%2F1%2FPullResults%2F181-199%2Fdatasets%2F9&expandedSection=metadata)

If link does not work, search for `Estonia` --> `Geospatial Aid Application Estonia Agricultural parcels` on the [INSPIRE](https://inspire-geoportal.ec.europa.eu/overview.html?view=thematicEuOverview&theme=none) platform.

#### License Terms
##### Conditions Applying To Access And Use
[Andmete kasutamisel nõustute Creative Commons 3.0 litsentsiga](https://creativecommons.org/licenses/by-sa/3.0/ee/legalcode)
##### Limitations On Public Access
avaliku juurdepääsu piirangud puuduvad (_no public access restrictions_)


### Lithuania

#### Data Source
[geoportal.lt](https://www.geoportal.lt/geoportal/nacionaline-mokejimo-agentura-prie-zemes-ukio-ministerijos#savedSearchId={772172A4-6719-48BD-8DDC-5DEEFB27DE74}&collapsed=true)
#### License Terms
From [Metadata](https://www.geoportal.lt/metadata-catalog/catalog/search/resource/details.page?uuid=%7B7AF3F5B2-DC58-4EC5-916C-813E994B2DCF%7D):
```
Aprašas (Citation)
Metaduomenys (Metadata) / Duomenų resursas (1) (Data Identification (1)) / Aprašas (Citation)
    Pavadinimas (Title): Lietuvos Respublikos teritorijos žemės ūkio naudmenų ir pasėlių plotų, auginamų kultūrų duomenų rinkinys (Data set on the farmland, cropland and crop types of the territory of the Republic of Lithuania)
    Sutrumpintas pavadinimas (Alternate Title): NMA-paseliai (NMA-paseliai)
    Data (Date)
    Metaduomenys (Metadata) / Duomenų resursas (1) (Data Identification (1)) / Aprašas (Citation) / Data (Date)
        Data (Date): 2021-10-08
        Datos tipas (Date Type): Revizija (Revision)
    Unikalus ištekliaus identifikatorius (Unique Resource Identifier): {BFDC920B-3F62-43D6-87F7-EF46B78D4847}
```

```
Teisiniai apribojimai (1) (Legal Constraints (1))
Metaduomenys (Metadata) / Duomenų resursas (1) (Data Identification (1)) / Teisiniai apribojimai (1) (Legal Constraints (1))
	Naudojimo ribotumas (Use Limitation): Tik nekomerciniam naudojimui (Non-commercial use only)
	Prieigos apribojimai (Access Constraints): Autoriaus teisės (Copyright)
	Naudojimo apribojimai (Use Constraints): Autoriaus teisės (Copyright)
```
[Copyright](https://www.geoportal.lt/geoportal/en/web/en/copyright)



