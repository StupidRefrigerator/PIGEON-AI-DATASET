"""Census preparation and approved geographic selection, without component IDs."""
import json
import geopandas as gpd
import pandas as pd

from .common import ROOT, RAW, INTERIM, CRS, read_ids, require

DENSITY_THRESHOLD = 500
SA1_PATH = RAW / "abs_sa1_2021/SA1_2021_AUST_GDA2020.shp"


def prepare_population():
    source = RAW / "census_2021/2021 Census GCP Statistical Area 1 for NSW/2021Census_G01_NSW_SA1.csv"
    population = pd.read_csv(source, usecols=["SA1_CODE_2021", "Tot_P_P"],
                             dtype={"SA1_CODE_2021": str})
    population = population.rename(columns={"SA1_CODE_2021": "sa1_code", "Tot_P_P": "population"})
    require(population.sa1_code.is_unique, "Duplicate Census SA1 IDs")
    require(population.population.notna().all() and (population.population >= 0).all(),
            "Missing or negative Census population")
    (INTERIM / "population").mkdir(parents=True, exist_ok=True)
    population.to_csv(INTERIM / "population/sa1_population_2021.csv", index=False)
    return population


def load_sa1(population):
    sa1 = gpd.read_file(SA1_PATH)
    sa1["sa1_code"] = sa1.SA1_CODE21.astype(str)
    require(sa1.sa1_code.is_unique, "Duplicate boundary SA1 IDs")
    return sa1.merge(population, on="sa1_code", how="left", validate="one_to_one")


def build_study(sa1):
    """Reconstruct raw SA1 polygons using a versioned geographic decision registry.

    The approved area demonstrably originated from a 50-density exploratory run.
    A 500-density replacement cannot be claimed to reproduce that recipe. The
    registry freezes the approved preliminary membership; the growth exclusion
    is recalculated spatially. Density 500 defines the urban core for diagnostics,
    not a new boundary. See docs/methodology.md.
    """
    selection = json.loads((ROOT / "docs/study_selection.json").read_text())
    sydney = sa1.loc[sa1.GCC_NAME21.eq("Greater Sydney")].copy()
    require(sydney.population.notna().all(), "Missing Greater Sydney population")
    sydney["pop_density"] = sydney.population / sydney.AREASQKM21.replace(0, float("nan"))
    approved_preliminary = read_ids(ROOT / "docs/approved_preliminary_sa1_ids.txt")
    require(approved_preliminary <= set(sydney.sa1_code), "Approved selection IDs absent from raw Sydney SA1s")
    preliminary = sydney[sydney.sa1_code.isin(approved_preliminary)].to_crs(CRS)
    boundaries = gpd.read_file(RAW / "abs_boundaries/GCCSA_2026_AUST_GDA2020.shp")
    boundary = boundaries[boundaries.GCC_NAME26.eq("Greater Sydney")]
    require(len(boundary) == 1, "Expected exactly one Greater Sydney boundary")
    suburbs = gpd.read_file(RAW / "abs_suburbs/SAL_2026_AUST_GDA2020.shp").to_crs(boundary.crs)
    suburbs = suburbs[suburbs.STE_NAME26.eq("New South Wales")]
    suburbs = suburbs[suburbs.representative_point().intersects(boundary.geometry.union_all())]
    growth = suburbs[suburbs.SAL_NAME26.isin(selection["growth_suburbs"])].to_crs(CRS)
    require(set(growth.SAL_NAME26) == set(selection["growth_suburbs"]), "Growth suburb names do not all match")
    final = preliminary[~preliminary.representative_point().intersects(growth.geometry.union_all())].copy()
    require(set(final.sa1_code) == read_ids(ROOT / "docs/approved_final_sa1_ids.txt"),
            "Rebuilt study area differs from approved final SA1 membership")
    require(len(final) == 10503, "Unexpected final study count")
    diagnostics = {"density_threshold": DENSITY_THRESHOLD,
                   "greater_sydney_sa1s": len(sydney),
                   "urban_core_sa1s_at_500": int((sydney.pop_density >= DENSITY_THRESHOLD).sum()),
                   "preliminary_sa1s": len(preliminary), "excluded_growth_sa1s": len(preliminary) - len(final),
                   "final_sa1s": len(final),
                   "selection_method": "approved preliminary SA1 registry + spatial growth-suburb exclusion"}
    return preliminary, final, diagnostics
