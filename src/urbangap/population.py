import geopandas as gpd

from .common import CRS, RADII, require


def population_context(sa1, zones):
    context = sa1.to_crs(CRS)
    context = context[context.intersects(zones.geometry.union_all())].copy()
    require(context.geometry.notna().all() and context.is_valid.all(), "Invalid contextual SA1 geometry")
    require(context.population.notna().all() and (context.population >= 0).all(), "Missing contextual population")
    # Selection above does not clip geometries. Preserve COMPLETE original areas.
    context["sa1_area_m2"] = context.area
    require((context.sa1_area_m2 > 0).all(), "Non-positive original SA1 area")
    return context


def allocate_population(zones, context):
    intersections = gpd.overlay(zones[["hex_id", "geometry"]],
                                context[["population", "sa1_area_m2", "geometry"]],
                                how="intersection", keep_geom_type=True)
    contribution = intersections.population * intersections.area / intersections.sa1_area_m2
    return contribution.groupby(intersections.hex_id).sum(min_count=1)


def add_population_features(grid, sa1):
    grid = grid.copy()
    context = population_context(sa1, grid)
    grid["population_est"] = grid.hex_id.map(allocate_population(grid, context)).fillna(0)
    grid["population_density"] = grid.population_est / (grid.area / 1e6)
    return grid


def add_population_buffers(grid, sa1):
    grid = grid.copy()
    # Use the same union-of-grid 500 m selection as the historical implementation.
    context_shape = grid.geometry.union_all().buffer(max(RADII))
    context_zones = gpd.GeoDataFrame(geometry=[context_shape], crs=CRS)
    context = population_context(sa1, context_zones)
    for radius in RADII:
        zones = grid[["hex_id", "geometry"]].copy()
        zones.geometry = zones.centroid.buffer(radius)  # GeoPandas default: 16 segments/quadrant.
        grid[f"population_{radius}m"] = grid.hex_id.map(allocate_population(zones, context)).fillna(0)
    return grid, {"context_sa1s": len(context), "context_population": float(context.population.sum())}
