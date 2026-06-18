# -*- coding: utf-8 -*-
"""Create V4 OSM Y-offset corrected polygon layer."""
# -*- coding: utf-8 -*-
import csv
import math
from qgis.core import (
    QgsProject, QgsVectorLayer, QgsFeature, QgsField, QgsGeometry, QgsPointXY,
    QgsFillSymbol, QgsRendererCategory, QgsCategorizedSymbolRenderer,
    QgsPalLayerSettings, QgsVectorLayerSimpleLabeling,
    QgsTextFormat, QgsTextBufferSettings
)
from qgis.PyQt.QtCore import QVariant
from qgis.PyQt.QtGui import QColor, QFont

CATEGORY_SIZES = {
    '城门': ('rect', 70, 70),
    '宫城': ('rect', 180, 140),
    '衙署': ('rect', 80, 80),
    '坊巷': ('rect', 140, 35),
    '桥梁': ('rect', 60, 20),
    '寺观': ('circle', 45, 24),
    '仓储': ('rect', 90, 70),
    '市场': ('rect', 100, 60),
    '水体': ('rect', 160, 50),
    '山体': ('circle', 80, 28),
    '园苑': ('rect', 120, 90),
    '军事': ('rect', 100, 80),
    '道路': ('rect', 160, 25),
    '其他': ('rect', 60, 60),
}

CATEGORY_COLORS = {
    '城门': QColor(190, 60, 45, 145),
    '宫城': QColor(210, 150, 40, 145),
    '衙署': QColor(85, 120, 190, 145),
    '坊巷': QColor(160, 120, 80, 130),
    '桥梁': QColor(90, 160, 190, 145),
    '寺观': QColor(120, 170, 90, 145),
    '仓储': QColor(140, 110, 70, 145),
    '市场': QColor(210, 120, 80, 145),
    '水体': QColor(70, 150, 210, 125),
    '山体': QColor(90, 140, 75, 145),
    '园苑': QColor(110, 175, 110, 135),
    '军事': QColor(120, 120, 120, 150),
    '道路': QColor(200, 110, 50, 135),
    '其他': QColor(160, 160, 160, 130),
}

def make_rect(x, y, width, height):
    hw, hh = width / 2.0, height / 2.0
    pts = [
        QgsPointXY(x - hw, y - hh), QgsPointXY(x + hw, y - hh),
        QgsPointXY(x + hw, y + hh), QgsPointXY(x - hw, y + hh),
        QgsPointXY(x - hw, y - hh),
    ]
    return QgsGeometry.fromPolygonXY([pts])

def make_circle(x, y, radius, segments=24):
    pts = []
    for i in range(segments + 1):
        a = 2 * math.pi * i / segments
        pts.append(QgsPointXY(x + radius * math.cos(a), y + radius * math.sin(a)))
    return QgsGeometry.fromPolygonXY([pts])

def geometry_for_place(p):
    cat = p.get('Category', '其他')
    x, y = float(p['X']), float(p['Y'])
    spec = CATEGORY_SIZES.get(cat, CATEGORY_SIZES['其他'])
    if spec[0] == 'circle':
        return make_circle(x, y, spec[1], spec[2])
    return make_rect(x, y, spec[1], spec[2])

def build_layer(places, layer_name):
    layer = QgsVectorLayer('Polygon?crs=EPSG:3857', layer_name, 'memory')
    provider = layer.dataProvider()
    provider.addAttributes([
        QgsField('Name', QVariant.String),
        QgsField('Category', QVariant.String),
        QgsField('X', QVariant.Double),
        QgsField('Y', QVariant.Double),
        QgsField('Confidence', QVariant.String),
        QgsField('Reference_Logic', QVariant.String),
    ])
    layer.updateFields()

    features = []
    for p in places:
        f = QgsFeature(layer.fields())
        f.setGeometry(geometry_for_place(p))
        f.setAttributes([p['Name'], p['Category'], float(p['X']), float(p['Y']), p['Confidence'], p['Reference_Logic']])
        features.append(f)
    provider.addFeatures(features)
    layer.updateExtents()

    categories = []
    for cat, color in CATEGORY_COLORS.items():
        symbol = QgsFillSymbol.createSimple({'outline_color': '50,50,50,180', 'outline_width': '0.25'})
        symbol.setColor(color)
        categories.append(QgsRendererCategory(cat, symbol, cat))
    layer.setRenderer(QgsCategorizedSymbolRenderer('Category', categories))

    label_settings = QgsPalLayerSettings()
    label_settings.fieldName = 'Name'
    label_settings.enabled = True
    text_format = QgsTextFormat()
    text_format.setFont(QFont('Microsoft YaHei'))
    text_format.setSize(10)
    buffer = QgsTextBufferSettings()
    buffer.setEnabled(True)
    buffer.setSize(1.2)
    buffer.setColor(QColor(255, 255, 255, 220))
    text_format.setBuffer(buffer)
    label_settings.setFormat(text_format)
    layer.setLabelsEnabled(True)
    layer.setLabeling(QgsVectorLayerSimpleLabeling(label_settings))

    QgsProject.instance().addMapLayer(layer)
    print('已生成 ' + layer_name + '，要素数量:', len(features))
    return layer

places = [{'Name': '余杭门', 'Category': '城门', 'X': 13375474.9, 'Y': 3538990.1, 'Confidence': 'high', 'Reference_Logic': '死锚：临安_十三城门图层坐标；Direction=北城墙; Status=已毁'}, {'Name': '艮山门', 'Category': '城门', 'X': 13377784.6, 'Y': 3539118.4, 'Confidence': 'high', 'Reference_Logic': '死锚：临安_十三城门图层坐标；Direction=北城墙; Status=已毁'}, {'Name': '东青门', 'Category': '城门', 'X': 13377935.0, 'Y': 3537007.8, 'Confidence': 'high', 'Reference_Logic': '死锚：临安_十三城门图层坐标；Direction=东城墙; Status=已毁'}, {'Name': '崇新门', 'Category': '城门', 'X': 13377797.9, 'Y': 3535600.8, 'Confidence': 'high', 'Reference_Logic': '死锚：临安_十三城门图层坐标；Direction=东城墙; Status=已毁'}, {'Name': '新开门', 'Category': '城门', 'X': 13377412.9, 'Y': 3534353.0, 'Confidence': 'high', 'Reference_Logic': '死锚：临安_十三城门图层坐标；Direction=东城墙; Status=已毁'}, {'Name': '保安门', 'Category': '城门', 'X': 13377399.7, 'Y': 3533649.5, 'Confidence': 'high', 'Reference_Logic': '死锚：临安_十三城门图层坐标；Direction=东城墙; Status=已毁'}, {'Name': '候潮门', 'Category': '城门', 'X': 13377244.8, 'Y': 3533074.3, 'Confidence': 'high', 'Reference_Logic': '死锚：临安_十三城门图层坐标；Direction=东城墙; Status=已毁'}, {'Name': '便门', 'Category': '城门', 'X': 13377351.0, 'Y': 3532578.7, 'Confidence': 'high', 'Reference_Logic': '死锚：临安_十三城门图层坐标；Direction=东城墙; Status=已毁'}, {'Name': '嘉会门', 'Category': '城门', 'X': 13376882.0, 'Y': 3531720.3, 'Confidence': 'high', 'Reference_Logic': '死锚：临安_十三城门图层坐标；Direction=南城墙; Status=已毁'}, {'Name': '钱湖门', 'Category': '城门', 'X': 13375289.1, 'Y': 3533499.1, 'Confidence': 'high', 'Reference_Logic': '死锚：临安_十三城门图层坐标；Direction=西城墙; Status=已毁'}, {'Name': '清波门', 'Category': '城门', 'X': 13375550.1, 'Y': 3534472.5, 'Confidence': 'high', 'Reference_Logic': '死锚：临安_十三城门图层坐标；Direction=西城墙; Status=已毁'}, {'Name': '涌金门', 'Category': '城门', 'X': 13375704.7, 'Y': 3535467.9, 'Confidence': 'high', 'Reference_Logic': '死锚：临安_十三城门图层坐标；Direction=西城墙; Status=已毁'}, {'Name': '钱塘门', 'Category': '城门', 'X': 13375514.8, 'Y': 3537034.4, 'Confidence': 'high', 'Reference_Logic': '死锚：临安_十三城门图层坐标；Direction=西城墙; Status=已毁'}, {'Name': '御街北段', 'Category': '道路', 'X': 13375718.7, 'Y': 3538550.0, 'Confidence': 'high', 'Reference_Logic': 'V3硬校准：直接取imperial_street线在3538550m处的代表点'}, {'Name': '御街中段', 'Category': '道路', 'X': 13376963.8, 'Y': 3536100.0, 'Confidence': 'high', 'Reference_Logic': 'V3硬校准：直接取imperial_street线在3536100m处的代表点'}, {'Name': '御街南段', 'Category': '道路', 'X': 13376807.3, 'Y': 3533420.0, 'Confidence': 'high', 'Reference_Logic': 'V3硬校准：直接取imperial_street线在皇城北侧附近的代表点'}, {'Name': '景灵宫', 'Category': '宫城', 'X': 13376468.1, 'Y': 3538510.0, 'Confidence': 'medium', 'Reference_Logic': 'V3校准：以imperial_street北段为轴，置于御街西侧、钱塘门东北侧宫观区；V4全局纠偏：依据QGIS+OSM目视检查，非硬锚地名整体向北平移650m'}, {'Name': '贡院', 'Category': '衙署', 'X': 13376846.9, 'Y': 3538420.0, 'Confidence': 'medium', 'Reference_Logic': 'V3校准：以imperial_street北段为轴，置于景灵宫东侧、御街东侧贡院区；V4全局纠偏：依据QGIS+OSM目视检查，非硬锚地名整体向北平移650m'}, {'Name': '天庆观', 'Category': '寺观', 'X': 13376804.4, 'Y': 3537590.0, 'Confidence': 'medium', 'Reference_Logic': 'V3校准：按御街中北段西侧寺观带重估，相对御街向西约95m；V4全局纠偏：依据QGIS+OSM目视检查，非硬锚地名整体向北平移650m'}, {'Name': '丰储仓', 'Category': '仓储', 'X': 13377199.7, 'Y': 3537550.0, 'Confidence': 'medium', 'Reference_Logic': 'V3校准：参照里南叠合图丰储仓标注，位于御街东侧、东青门西南、崇新门以北；V4全局纠偏：依据QGIS+OSM目视检查，非硬锚地名整体向北平移650m'}, {'Name': '中书省', 'Category': '衙署', 'X': 13377023.6, 'Y': 3537860.0, 'Confidence': 'medium', 'Reference_Logic': 'V3校准：按御街中北段东侧官署带重估，相对御街向东约145m；V4全局纠偏：依据QGIS+OSM目视检查，非硬锚地名整体向北平移650m'}, {'Name': '太常寺', 'Category': '衙署', 'X': 13376953.9, 'Y': 3538130.0, 'Confidence': 'low', 'Reference_Logic': 'V3校准：位于御街北部东侧官署带，文字/位置低置信，按东偏约165m估算；V4全局纠偏：依据QGIS+OSM目视检查，非硬锚地名整体向北平移650m'}, {'Name': '宗正寺', 'Category': '衙署', 'X': 13377131.7, 'Y': 3537980.0, 'Confidence': 'low', 'Reference_Logic': 'V3校准：位于太常寺东南侧官署带，文字/位置低置信，按东偏约285m估算；V4全局纠偏：依据QGIS+OSM目视检查，非硬锚地名整体向北平移650m'}, {'Name': '殿前司', 'Category': '军事', 'X': 13377128.0, 'Y': 3535330.0, 'Confidence': 'medium', 'Reference_Logic': 'V3校准：以imperial_street中南段为轴，置于御街东侧、新开门西北官署/军事区；V4全局纠偏：依据QGIS+OSM目视检查，非硬锚地名整体向北平移650m'}, {'Name': '德寿宫', 'Category': '宫城', 'X': 13377151.9, 'Y': 3534470.0, 'Confidence': 'medium', 'Reference_Logic': 'V3校准：以imperial_street南段为轴，置于御街东侧、保安门西北宫苑区；V4全局纠偏：依据QGIS+OSM目视检查，非硬锚地名整体向北平移650m'}, {'Name': '东菜市', 'Category': '市场', 'X': 13377239.1, 'Y': 3534910.0, 'Confidence': 'medium', 'Reference_Logic': 'V3城墙内约束：参照新开门内侧与御街之间，回移至东城墙内的市场区；V4全局纠偏：依据QGIS+OSM目视检查，非硬锚地名整体向北平移650m'}, {'Name': '临安府', 'Category': '衙署', 'X': 13375950.0, 'Y': 3534550.0, 'Confidence': 'medium', 'Reference_Logic': 'V3微调：位于太学南侧、清波门东南，参照城墙/御街/太学关系；V4全局纠偏：依据QGIS+OSM目视检查，非硬锚地名整体向北平移650m'}, {'Name': '太学', 'Category': '衙署', 'X': 13375830.0, 'Y': 3534970.0, 'Confidence': 'medium', 'Reference_Logic': 'V3微调：位于清波门东北、御街西侧，参照叠合图点位；V4全局纠偏：依据QGIS+OSM目视检查，非硬锚地名整体向北平移650m'}, {'Name': '六部', 'Category': '衙署', 'X': 13376248.8, 'Y': 3533870.0, 'Confidence': 'medium', 'Reference_Logic': 'V3校准：参照御街南端与皇城西北，置于御街西侧官署区；V4全局纠偏：依据QGIS+OSM目视检查，非硬锚地名整体向北平移650m'}, {'Name': '三省六部', 'Category': '衙署', 'X': 13376083.7, 'Y': 3533815.0, 'Confidence': 'medium', 'Reference_Logic': 'V3校准：参照皇城西北与御街南端，置于御街西侧较远官署区；V4全局纠偏：依据QGIS+OSM目视检查，非硬锚地名整体向北平移650m'}, {'Name': '秘书省', 'Category': '衙署', 'X': 13376540.1, 'Y': 3533830.0, 'Confidence': 'medium', 'Reference_Logic': 'V3校准：参照御街南端与皇城北侧，置于皇城北侧偏西官署区；V4全局纠偏：依据QGIS+OSM目视检查，非硬锚地名整体向北平移650m'}, {'Name': '中瓦', 'Category': '市场', 'X': 13376497.3, 'Y': 3534070.0, 'Confidence': 'medium', 'Reference_Logic': 'V3校准：以御街南段为轴，置于皇城北侧、御街西侧瓦子区；V4全局纠偏：依据QGIS+OSM目视检查，非硬锚地名整体向北平移650m'}, {'Name': '北瓦', 'Category': '市场', 'X': 13376540.7, 'Y': 3536130.0, 'Confidence': 'low', 'Reference_Logic': 'V3校准：以御街中段为轴，置于御街西侧瓦子区，低置信；V4全局纠偏：依据QGIS+OSM目视检查，非硬锚地名整体向北平移650m'}, {'Name': '南瓦', 'Category': '市场', 'X': 13376333.7, 'Y': 3533815.0, 'Confidence': 'low', 'Reference_Logic': 'V3校准：参照皇城北侧与御街南端，置于御街西侧瓦子区，低置信；V4全局纠偏：依据QGIS+OSM目视检查，非硬锚地名整体向北平移650m'}, {'Name': '清河坊', 'Category': '坊巷', 'X': 13376040.0, 'Y': 3533470.0, 'Confidence': 'medium', 'Reference_Logic': 'V3微调：参照皇城西北、清波门东南和清河坊历史片区关系；V4全局纠偏：依据QGIS+OSM目视检查，非硬锚地名整体向北平移650m'}, {'Name': '众安桥', 'Category': '桥梁', 'X': 13376815.1, 'Y': 3536830.0, 'Confidence': 'low', 'Reference_Logic': 'V3校准：参照御街中段附近水道交会，较V2回收至御街西侧近轴低置信桥点；V4全局纠偏：依据QGIS+OSM目视检查，非硬锚地名整体向北平移650m'}, {'Name': '梅家桥', 'Category': '桥梁', 'X': 13377081.1, 'Y': 3536500.0, 'Confidence': 'low', 'Reference_Logic': 'V3校准：参照御街中段东侧水系，较V2微向东修正；V4全局纠偏：依据QGIS+OSM目视检查，非硬锚地名整体向北平移650m'}, {'Name': '盐桥', 'Category': '桥梁', 'X': 13377181.0, 'Y': 3536730.0, 'Confidence': 'low', 'Reference_Logic': 'V3校准：参照御街中段东侧、崇新门西南方向，回收过度东偏；V4全局纠偏：依据QGIS+OSM目视检查，非硬锚地名整体向北平移650m'}, {'Name': '丰乐桥', 'Category': '桥梁', 'X': 13376943.2, 'Y': 3535770.0, 'Confidence': 'low', 'Reference_Logic': 'V3校准：参照御街中南段附近桥梁带，轻微西偏；V4全局纠偏：依据QGIS+OSM目视检查，非硬锚地名整体向北平移650m'}, {'Name': '大内', 'Category': '宫城', 'X': 13376755.1, 'Y': 3532590.5, 'Confidence': 'high', 'Reference_Logic': 'V3硬校准：imperial_palace.geojson多边形质心'}, {'Name': '皇城', 'Category': '宫城', 'X': 13376790.1, 'Y': 3532605.5, 'Confidence': 'high', 'Reference_Logic': 'V3硬校准：imperial_palace.geojson多边形质心东偏，作为皇城面状代表点'}, {'Name': '南宋太庙', 'Category': '宫城', 'X': 13375680.0, 'Y': 3533515.0, 'Confidence': 'medium', 'Reference_Logic': 'V3微调：位于清波门以南、皇城西北侧，参照叠合图点位；V4全局纠偏：依据QGIS+OSM目视检查，非硬锚地名整体向北平移650m'}, {'Name': '龙翔宫', 'Category': '宫城', 'X': 13375490.0, 'Y': 3533110.0, 'Confidence': 'medium', 'Reference_Logic': 'V3微调：位于皇城西侧、南城墙北侧，参照南宋太庙/报恩寺关系；V4全局纠偏：依据QGIS+OSM目视检查，非硬锚地名整体向北平移650m'}, {'Name': '佑圣观', 'Category': '寺观', 'X': 13375680.0, 'Y': 3534350.0, 'Confidence': 'medium', 'Reference_Logic': 'V3微调：位于钱湖门东北、太学西南，参照叠合图点位；V4全局纠偏：依据QGIS+OSM目视检查，非硬锚地名整体向北平移650m'}, {'Name': '报恩寺', 'Category': '寺观', 'X': 13375350.0, 'Y': 3532910.0, 'Confidence': 'medium', 'Reference_Logic': 'V3微调：位于皇城西南、南城墙内侧，参照西湖南缘与城墙关系；V4全局纠偏：依据QGIS+OSM目视检查，非硬锚地名整体向北平移650m'}, {'Name': '新水池', 'Category': '水体', 'X': 13376705.1, 'Y': 3532958.5, 'Confidence': 'medium', 'Reference_Logic': 'V3校准：位于imperial_palace多边形南侧偏西，作为新水池代表点；V4全局纠偏：依据QGIS+OSM目视检查，非硬锚地名整体向北平移650m'}, {'Name': '中军堂', 'Category': '军事', 'X': 13376770.1, 'Y': 3532918.5, 'Confidence': 'medium', 'Reference_Logic': 'V3校准：位于imperial_palace多边形南侧中部，作为中军堂代表点；V4全局纠偏：依据QGIS+OSM目视检查，非硬锚地名整体向北平移650m'}, {'Name': '修内司营', 'Category': '衙署', 'X': 13375610.0, 'Y': 3533255.0, 'Confidence': 'low', 'Reference_Logic': 'V3微调：参照皇城西侧官署/营区与龙翔宫、南宋太庙之间关系低置信；V4全局纠偏：依据QGIS+OSM目视检查，非硬锚地名整体向北平移650m'}, {'Name': '后苑', 'Category': '园苑', 'X': 13376765.1, 'Y': 3533492.0, 'Confidence': 'medium', 'Reference_Logic': 'V3校准：位于imperial_palace多边形北侧，作为后苑代表点；V4全局纠偏：依据QGIS+OSM目视检查，非硬锚地名整体向北平移650m'}, {'Name': '保俶塔', 'Category': '寺观', 'X': 13374880.0, 'Y': 3537130.0, 'Confidence': 'medium', 'Reference_Logic': 'V3西湖校准：位于钱塘门西南、西湖东北岸山体寺塔区，较V2向西修正；V4全局纠偏：依据QGIS+OSM目视检查，非硬锚地名整体向北平移650m'}, {'Name': '断桥', 'Category': '桥梁', 'X': 13374840.0, 'Y': 3536400.0, 'Confidence': 'medium', 'Reference_Logic': 'V3西湖校准：参照钱塘门/涌金门之间的西湖北岸桥位，较V2向西微调；V4全局纠偏：依据QGIS+OSM目视检查，非硬锚地名整体向北平移650m'}, {'Name': '孤山', 'Category': '山体', 'X': 13374740.0, 'Y': 3535870.0, 'Confidence': 'medium', 'Reference_Logic': 'V3西湖校准：参照西湖中北部孤山位置，较V2向湖心西移；V4全局纠偏：依据QGIS+OSM目视检查，非硬锚地名整体向北平移650m'}, {'Name': '宝石山', 'Category': '山体', 'X': 13374900.0, 'Y': 3537695.0, 'Confidence': 'medium', 'Reference_Logic': 'V3西湖校准：参照钱塘门西北、西湖北岸山体区，较V2向西修正；V4全局纠偏：依据QGIS+OSM目视检查，非硬锚地名整体向北平移650m'}, {'Name': '柳洲寺', 'Category': '寺观', 'X': 13375140.0, 'Y': 3534200.0, 'Confidence': 'low', 'Reference_Logic': 'V3微调：古图左页西湖南缘寺院文字疑似，参照钱湖门西北与西湖东岸低置信；V4全局纠偏：依据QGIS+OSM目视检查，非硬锚地名整体向北平移650m'}, {'Name': '石佛寺', 'Category': '寺观', 'X': 13374870.0, 'Y': 3537270.0, 'Confidence': 'low', 'Reference_Logic': 'V3西湖校准：古图左页西湖北岸寺院文字疑似，参照保俶塔/宝石山低置信；V4全局纠偏：依据QGIS+OSM目视检查，非硬锚地名整体向北平移650m'}, {'Name': '古曹婆寺', 'Category': '寺观', 'X': 13375080.0, 'Y': 3533150.0, 'Confidence': 'low', 'Reference_Logic': 'V3微调：古图左页西湖南侧寺院文字疑似，参照报恩寺西侧低置信；V4全局纠偏：依据QGIS+OSM目视检查，非硬锚地名整体向北平移650m'}, {'Name': '雷峰塔', 'Category': '寺观', 'X': 13375060.0, 'Y': 3533570.0, 'Confidence': 'medium', 'Reference_Logic': 'V3西湖南缘校准：参照西湖南侧塔寺位置与南宋太庙西侧关系；V4全局纠偏：依据QGIS+OSM目视检查，非硬锚地名整体向北平移650m'}, {'Name': '净慈寺', 'Category': '寺观', 'X': 13375020.0, 'Y': 3532970.0, 'Confidence': 'low', 'Reference_Logic': 'V3西湖南缘校准：参照雷峰塔与报恩寺之间，古图寺名低置信；V4全局纠偏：依据QGIS+OSM目视检查，非硬锚地名整体向北平移650m'}, {'Name': '小孤山', 'Category': '山体', 'X': 13374780.0, 'Y': 3535530.0, 'Confidence': 'low', 'Reference_Logic': 'V3西湖校准：参照孤山南侧水域山体疑似位置，低置信；V4全局纠偏：依据QGIS+OSM目视检查，非硬锚地名整体向北平移650m'}, {'Name': '三茅观', 'Category': '寺观', 'X': 13375320.0, 'Y': 3536850.0, 'Confidence': 'low', 'Reference_Logic': 'V3微调：参照西湖东岸与涌金门西北侧，宫观名低置信；V4全局纠偏：依据QGIS+OSM目视检查，非硬锚地名整体向北平移650m'}, {'Name': '东岳宫', 'Category': '寺观', 'X': 13376401.3, 'Y': 3537360.0, 'Confidence': 'low', 'Reference_Logic': 'V3校准：参照imperial_street与西湖东岸之间，古图宫观名低置信定位；V4全局纠偏：依据QGIS+OSM目视检查，非硬锚地名整体向北平移650m'}, {'Name': '水仙王庙', 'Category': '寺观', 'X': 13376741.5, 'Y': 3537340.0, 'Confidence': 'low', 'Reference_Logic': 'V3校准：参照imperial_street中北段西侧，古图庙名低置信定位；V4全局纠偏：依据QGIS+OSM目视检查，非硬锚地名整体向北平移650m'}, {'Name': '涌金池', 'Category': '水体', 'X': 13375460.0, 'Y': 3536230.0, 'Confidence': 'medium', 'Reference_Logic': 'V3校准：参照涌金门死锚西南侧水体，较V2贴近城门与湖岸；V4全局纠偏：依据QGIS+OSM目视检查，非硬锚地名整体向北平移650m'}, {'Name': '西湖', 'Category': '水体', 'X': 13374650.0, 'Y': 3535550.0, 'Confidence': 'medium', 'Reference_Logic': 'V3西湖校准：作为西湖水域代表点，较V2向湖心西移；V4全局纠偏：依据QGIS+OSM目视检查，非硬锚地名整体向北平移650m'}, {'Name': '东御街坊巷群', 'Category': '坊巷', 'X': 13377313.8, 'Y': 3536750.0, 'Confidence': 'low', 'Reference_Logic': 'V3校准：以imperial_street中段为轴，向东约350m表示御街东侧坊巷密集区；V4全局纠偏：依据QGIS+OSM目视检查，非硬锚地名整体向北平移650m'}, {'Name': '西御街坊巷群', 'Category': '坊巷', 'X': 13376603.8, 'Y': 3536750.0, 'Confidence': 'low', 'Reference_Logic': 'V3校准：以imperial_street中段为轴，向西约360m表示御街西侧坊巷密集区；V4全局纠偏：依据QGIS+OSM目视检查，非硬锚地名整体向北平移650m'}, {'Name': '新开门内坊巷', 'Category': '坊巷', 'X': 13377161.5, 'Y': 3535070.0, 'Confidence': 'low', 'Reference_Logic': 'V3城墙内约束：参照新开门死锚向城内西侧偏移，并与御街东侧街区协调；V4全局纠偏：依据QGIS+OSM目视检查，非硬锚地名整体向北平移650m'}, {'Name': '保安门内坊巷', 'Category': '坊巷', 'X': 13377079.0, 'Y': 3534300.0, 'Confidence': 'low', 'Reference_Logic': 'V3城墙内约束：参照保安门死锚向城内西侧偏移，并与御街东侧街区协调；V4全局纠偏：依据QGIS+OSM目视检查，非硬锚地名整体向北平移650m'}, {'Name': '候潮门内坊巷', 'Category': '坊巷', 'X': 13377003.5, 'Y': 3533710.0, 'Confidence': 'low', 'Reference_Logic': 'V3城墙内约束：参照候潮门死锚向城内西侧偏移，保留低置信；V4全局纠偏：依据QGIS+OSM目视检查，非硬锚地名整体向北平移650m'}, {'Name': '嘉会门内坊巷', 'Category': '坊巷', 'X': 13376780.0, 'Y': 3532610.0, 'Confidence': 'low', 'Reference_Logic': 'V3微调：参照嘉会门死锚向城内北侧偏移，避开南城墙边界；V4全局纠偏：依据QGIS+OSM目视检查，非硬锚地名整体向北平移650m'}, {'Name': '钱塘门内坊巷', 'Category': '坊巷', 'X': 13375760.0, 'Y': 3537695.0, 'Confidence': 'low', 'Reference_Logic': 'V3微调：参照钱塘门死锚向城内东侧偏移，结合西御街北段街区；V4全局纠偏：依据QGIS+OSM目视检查，非硬锚地名整体向北平移650m'}, {'Name': '清波门内坊巷', 'Category': '坊巷', 'X': 13375810.0, 'Y': 3535125.0, 'Confidence': 'low', 'Reference_Logic': 'V3微调：参照清波门死锚向城内东侧偏移，结合太学/临安府片区；V4全局纠偏：依据QGIS+OSM目视检查，非硬锚地名整体向北平移650m'}, {'Name': '涌金门内坊巷', 'Category': '坊巷', 'X': 13375930.0, 'Y': 3536135.0, 'Confidence': 'low', 'Reference_Logic': 'V3微调：参照涌金门死锚向城内东侧偏移，避免过近御街中轴；V4全局纠偏：依据QGIS+OSM目视检查，非硬锚地名整体向北平移650m'}]

build_layer(places, '临安_提取地名_面状_V4_OSM纠偏')
