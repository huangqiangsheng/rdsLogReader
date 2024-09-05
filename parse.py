import re
rotate_collision_txt = "[240810 131334.755][359,207,443][D][d] CheckRotateCollision4||vertices_size: 4||Polygon|(-63.933421,-52.596817)(-62.804479,-52.585421)(-62.786663,-54.350332)(-63.915605,-54.361728)|ClockwiseSectors||(center: (-62.585000,-51.326000), bound1: (-1.148000,-0.564500), bound2: (1.148000,0.564500))|(center: (-62.585000,-51.326000), bound1: (-1.148000,0.564500), bound2: (1.148000,-0.564500))|(center: (-62.585000,-51.326000), bound1: (0.617000,0.564500), bound2: (-0.617000,-0.564500))|(center: (-62.585000,-51.326000), bound1: (0.617000,-0.564500), bound2: (-0.617000,0.564500))|CollisionSector|(center: (-62.585000,-51.326000), bound1: (-1.148000,0.564500), bound2: (1.148000,-0.564500))|CounterclockwiseSectors||(center: (-62.585000,-51.326000), bound1: (1.148000,0.564500), bound2: (-1.148000,-0.564500))|(center: (-62.585000,-51.326000), bound1: (1.148000,-0.564500), bound2: (-1.148000,0.564500))|(center: (-62.585000,-51.326000), bound1: (-0.617000,-0.564500), bound2: (0.617000,0.564500))|(center: (-62.585000,-51.326000), bound1: (-0.617000,0.564500), bound2: (0.617000,-0.564500))"


polygon_regex = re.compile(".*\|Polygon\|(.*)\|(Clockwise|Counter).*")
polygon_out = polygon_regex.match(rotate_collision_txt)[1]
polygon_out = polygon_out.replace(')', '|').replace('(', '')
vertices_strs = polygon_out.split('|')
vertices = []
print("vertices_strs: ", vertices_strs)
for vertex_str in vertices_strs:
    if not vertex_str:
        continue
    if vertex_str in ['ClockwiseSectors', 'CounterclockwiseSectors', 'CollisionSector']:
        break
    x, y = vertex_str.split(',')
    vertices.append((float(x), float(y)))

print("vertices: ", vertices)

# sectors
sector_regex = re.compile(".*(Clockwise|Counterclockwise)Sectors\|\|(.*)\|CollisionSector.*")
sectors = sector_regex.match(rotate_collision_txt)
sectors_strs = sectors[2].split('|')
sectors = []
for sector_str in sectors_strs:
    # sector_str has format: (center: (-62.585000,-51.326000), bound1: (-1.148000,-0.564500), bound2: (1.143206,0.574147))
    if sector_str in ['', 'CounterclockwiseSectors', 'ClockwiseSectors', 'CollisionSector']:
        continue
    # remove first ( and last )
    sector_str = sector_str[1:-1]
    sector_str = sector_str.replace('center: ','').replace(', bound1: ', '|').replace(', bound2: ', '|')
    center, bound1, bound2 = sector_str.split('|')

    center_x, center_y = center[1:-1].split(',')
    bound1_x, bound1_y = bound1[1:-1].split(',')
    bound2_x, bound2_y = bound2[1:-1].split(',')
    sectors.append((float(center_x), float(center_y), float(bound1_x), float(bound1_y), float(bound2_x), float(bound2_y)))
print("sectors: ", sectors)

# collision sector
collision_sector_regex = re.compile(".*CollisionSector\|(.*)")
collision_sector_str = collision_sector_regex.match(rotate_collision_txt)[1].split('|')[0]
collision_sector_str = collision_sector_str[1:-1].replace('center: ','').replace(', bound1: ', '|').replace(', bound2: ', '|')
center, bound1, bound2 = collision_sector_str.split('|')
center_x, center_y = center[1:-1].split(',')
bound1_x, bound1_y = bound1[1:-1].split(',')
bound2_x, bound2_y = bound2[1:-1].split(',')
collision_sector=((float(center_x), float(center_y), float(bound1_x), float(bound1_y), float(bound2_x), float(bound2_y)))
print("collision_sector: ", collision_sector)
