# 地形与山体重制 · 2.2.0

本轮以山脉高度和视觉位置为重点，覆盖法国与原地图包含的邻国陆地。地图的省份轮廓、国家边界、首府胜利点与河流位置保留。

## 重制内容

- 高度图：以195块公开Terrarium高程瓦片重建5632×2048高度图，海拔使用米制数据；每32米对应一个灰度级，陆地零海拔从97起、海洋和湖泊保持89。
- 山体阴影：2816×1024法线图由新高度图计算，按本机原生渲染程序使用的通道顺序写入，消除旧阴影与新山体错位。
- 地表颜色：移除原卫星颜色图内烘焙的山体明暗和高山颜色，按新海拔和地表纹理生成自然色；高海拔岩石与积雪同步定位。
- 夜间灯光：原颜色图Alpha通道全为255，原生着色程序直接用该通道控制城市灯光。新蒙版仅绘制城镇纹理和已核对首府的近域；新增完整12级DXT5纹理缩小层级。
- 植被：保留低地树木与风格，将水面和2000米以上的树木移除。城市图 cities.bmp 负责建筑风格，逐字节保留。
- 模型贴地：只调整建筑和部队模型的垂直坐标，保留原地面偏移，横向位置、旋转、类型与数量不变。
- 省份地形：以新纹理中的地形面积确定省份战斗地形，修正6362处。省份ID、颜色、陆海属性、沿海标记与大洲不变。

山体包括阿尔卑斯、比利牛斯、中央高原、孚日、汝拉、黑森林和科西嘉。巴黎盆地、波河平原、卢瓦尔河谷和罗讷河谷用独立坐标检查低海拔，避免为增强山体效果而把平原整体抬高。

## 数据与限制

采用Mapzen Terrain Tiles on AWS的公开高程数据，下载于2026年10月2日。瓦片为8级Web Mercator，欧洲地区地面采样间距约400米；游戏像素及8位高度图会进一步平均峰顶与狭窄河谷。新格网采样最高约4593米，这不是对真实山峰最高海拔的重新测量。

现有地图与地理坐标通过法国政府市镇定位点拟合，留一法均方根误差约6.2像素；此误差应与省份形状简化一起考虑。森林和低地土地覆盖纹理沿用原模组，没有制作1936年的土地覆盖调查。

对照图使用两份高度图、相同色阶与相同光照渲染，属于数据核对图，不是游戏截图。静态地图、贴地坐标及安装字节验证不等于游戏内显示测试；需重启游戏、新开档确认。

## 来源与署名

- [Terrain Tiles公开数据登记](https://registry.opendata.aws/terrain-tiles/)
- [Terrarium米制高程编码](https://github.com/tilezen/joerd/blob/master/docs/formats.md)
- [高程资料归属与署名要求](https://github.com/tilezen/joerd/blob/master/docs/attribution.md)
- [法国政府市镇坐标](https://geo.api.gouv.fr/decoupage-administratif/communes)
- [勃朗峰官方旅游资料](https://www.chamonix.com/la-vallee/incontournables/le-mont-blanc)、[桑西山资料](https://www.sancy.com/decouvrir/incontournables/puy-de-sancy/)、[汝拉自然公园地形资料](https://www.parc-haut-jura.fr/)

Europe terrain data produced using Copernicus data and information funded by the European Union - EU-DEM layers; global GMTED2010 and SRTM terrain data courtesy of the U.S. Geological Survey; Mapzen Terrain Tiles on AWS.

全部瓦片来源、SHA-256、投影参数与原地图输入哈希在工作目录 terrain-pass 中保存。独立包只包含生成的游戏地图文件和本说明；原工坊数据与此前整合版压缩包保留。
