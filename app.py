from flask import Flask, request, jsonify, render_template
import math
import os
import sys
from dotenv import load_dotenv
from flask_cors import CORS
from datetime import datetime
from kp_profiles import PROFILES, get_profile, get_profiles_list, get_dimensions_correction_factor

app = Flask(__name__)
# Разрешаем CORS для всех доменов
CORS(app, resources={r"/*": {"origins": "*"}})
load_dotenv()

# Настройка логирования для отладки
@app.before_request
def log_request_info():
    app.logger.debug('Headers: %s', request.headers)
    app.logger.debug('Body: %s', request.get_data())
    
@app.after_request
def after_request(response):
    # Добавляем заголовки CORS для всех запросов
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

def calculate_basic_dimensions(length, width, depth, wall_thickness, profile_id="kp1"):
    """
    Расчет основных размеров бассейна с учетом профиля КП
    
    Args:
        length (float): Длина бассейна в мм
        width (float): Ширина бассейна в мм
        depth (float): Глубина бассейна в мм
        wall_thickness (float): Толщина стен в мм
        profile_id (str): Идентификатор профиля КП
        
    Returns:
        dict: Словарь с основными размерами
    """
    # Получаем параметры профиля
    profile = get_profile(profile_id)
    
    # Конвертируем размеры в метры
    length_m = length / 1000
    width_m = width / 1000
    depth_m = depth / 1000
    wall_thickness_m = wall_thickness / 1000
    
    # Рассчитываем теоретические размеры
    theoretical_water_surface = length_m * width_m
    theoretical_perimeter = 2 * (length_m + width_m)
    theoretical_wall_area = theoretical_perimeter * depth_m
    theoretical_finishing_area = theoretical_water_surface + theoretical_wall_area
    theoretical_water_volume = theoretical_water_surface * depth_m
    
    # Получаем коэффициенты корректировки
    correction_factors = get_dimensions_correction_factor(profile_id, {
        "length": length,
        "width": width,
        "depth": depth
    })
    
    # Применяем корректировку
    water_surface = theoretical_water_surface * correction_factors["water_surface"]
    perimeter = theoretical_perimeter * correction_factors["perimeter"]
    wall_area = theoretical_wall_area * correction_factors["wall_area"]
    finishing_area = theoretical_finishing_area * correction_factors["finishing_area"]
    water_volume = theoretical_water_volume * correction_factors["water_volume"]
    
    # Рассчитываем объем бетона
    concrete_volume = (water_surface * wall_thickness_m) + (wall_area * wall_thickness_m)
    
    # Рассчитываем объем земляных работ (примерно в 2 раза больше объема бассейна)
    earth_volume = water_volume * 2
    
    # Форматируем вывод
    return {
        "Площадь водного зеркала": f"{water_surface:.1f} м²",
        "Периметр": f"{perimeter:.1f} м",
        "Площадь стен": f"{wall_area:.1f} м²",
        "Площадь под отделку": f"{finishing_area:.1f} м²",
        "Объем воды": f"{water_volume:.1f} м³",
        "Объем бетона": f"{concrete_volume:.1f} м³",
        "Объем земляных работ": f"{earth_volume:.1f} м³"
    }

def calculate_earthworks(length, width, depth, wall_thickness):
    """Расчет земляных работ"""
    # Переводим в метры
    l, w, d = length/1000, width/1000, depth/1000
    wt = wall_thickness/1000
    
    # Размеры котлована (добавляем по 600мм с каждой стороны для работы)
    pit_length = l + 2*wt + 1.2  # +600мм с каждой стороны
    pit_width = w + 2*wt + 1.2   # +600мм с каждой стороны
    
    # Глубина котлована (добавляем толщину подбетонки и щебня)
    pit_depth = d + wt + 0.2  # +100мм щебень и +100мм подбетонка
    
    # Площадь котлована
    pit_area = pit_length * pit_width
    
    # Объем котлована
    pit_volume = pit_area * pit_depth
    
    # Объем обратной засыпки (объем котлована минус объем бассейна)
    pool_volume = (l + 2*wt) * (w + 2*wt) * (d + wt)
    backfill_volume = pit_volume - pool_volume
    
    # Количество КамАЗов для вывоза грунта (объем кузова ~8м³)
    trucks = math.ceil(pit_volume / 8)
    
    return {
        "Глубина котлована": f"{pit_depth:.2f} м",
        "Длина котлована": f"{pit_length:.2f} м",
        "Ширина котлована": f"{pit_width:.2f} м",
        "Площадь котлована": f"{pit_area:.1f} м²",
        "Объем котлована": f"{pit_volume:.1f} м³",
        "Объем обратной засыпки": f"{backfill_volume:.1f} м³",
        "Количество КамАЗов": f"{trucks}"
    }

def calculate_concrete_works(length, width, depth, wall_thickness):
    """Расчет бетонных работ"""
    # Переводим в метры
    l, w, d = length/1000, width/1000, depth/1000
    wt = wall_thickness/1000
    
    # Расчет объема бетона для подбетонки (М200)
    base_length = l + 1.2  # добавляем по 600мм с каждой стороны
    base_width = w + 1.2   # добавляем по 600мм с каждой стороны
    base_volume = base_length * base_width * 0.1  # толщина 100мм
    
    # Расчет объема щебня
    gravel_volume = base_length * base_width * 0.1  # толщина 100мм
    
    # Расчет объема бетона для чаши (М300)
    # Объем дна
    bottom_volume = (l + 2*wt) * (w + 2*wt) * wt
    
    # Объем стен
    wall_volume = ((l + 2*wt) * 2 + (w + 2*wt) * 2) * d * wt
    
    # Объем бортиков (высота 150мм, ширина 300мм)
    border_height = 0.15
    border_width = 0.3
    border_length = (l + 2*wt) * 2 + (w + 2*wt) * 2
    border_volume = border_length * border_height * border_width
    
    # Общий объем бетона для чаши
    bowl_volume = bottom_volume + wall_volume + border_volume
    
    total_volume = base_volume + bowl_volume
    
    return {
        "Щебень": f"{gravel_volume:.1f} м³",
        "Бетон M200 (подбетонка)": f"{base_volume:.1f} м³",
        "Бетон М300 (чаша)": f"{bowl_volume:.1f} м³",
        "Общий объем бетона": f"{total_volume:.1f} м³"
    }

def calculate_formwork(length, width, depth, wall_thickness):
    """Расчет опалубки и армирования"""
    # Переводим в метры
    l, w, d = length/1000, width/1000, depth/1000
    wt = wall_thickness/1000
    
    # Расчет площади опалубки
    # Внешняя опалубка: периметр внешней части бассейна * глубину
    outer_perimeter = 2 * ((l + 2*wt) + (w + 2*wt))
    outer_formwork_area = outer_perimeter * d
    
    # Внутренняя опалубка: периметр внутренней части бассейна * глубину
    inner_perimeter = 2 * (l + w)
    inner_formwork_area = inner_perimeter * d
    
    # Общая площадь опалубки
    total_formwork_area = outer_formwork_area + inner_formwork_area
    
    # Расчет количества фанеры (лист 1.5м x 1.5m = 2.25m²)
    plywood_sheets = math.ceil(total_formwork_area / 2.25)
    
    # Расчет веса арматуры
    # Примерный расход арматуры: 100 кг/м³ бетона
    concrete_volume = (outer_perimeter * wt * d) + ((l + 2*wt) * (w + 2*wt) * wt)
    rebar_weight = concrete_volume * 100  # 100 кг/м³
    
    return {
        "Площадь опалубки": f"{total_formwork_area:.1f} м²",
        "Количество фанеры": f"{plywood_sheets} листов",
        "Вес арматуры": f"{rebar_weight:.0f} кг"
    }

def calculate_finishing_cost(basic_dims, profile_id="kp1"):
    """
    Расчет стоимости отделочных работ с учетом профиля КП
    
    Args:
        basic_dims (dict): Словарь с основными размерами
        profile_id (str): Идентификатор профиля КП
        
    Returns:
        dict: Словарь с расчетами стоимости отделочных работ
    """
    # Получаем параметры профиля
    profile = get_profile(profile_id)
    
    # Получаем числовые значения из строк
    finishing_area = float(basic_dims["Площадь под отделку"].split()[0])
    
    # Получаем цены из профиля
    prices = profile["materials_prices"]
    works_prices = profile["works_prices"]
    
    # Расчет стоимости материалов
    materials_cost = {
        "Плитка": finishing_area * prices["tile"],
        "Затирка": finishing_area * prices["grout"],
        "Клей для плитки": finishing_area * prices["tile_adhesive"],
        "Гидроизоляция": finishing_area * prices["waterproofing"]
    }
    
    # Расчет стоимости работ
    works_cost = {
        "Укладка плитки": finishing_area * works_prices["tile_laying"],
        "Затирка швов": finishing_area * works_prices["grouting"]
    }
    
    # Общая стоимость
    total_cost = sum(materials_cost.values()) + sum(works_cost.values())
    
    # Форматируем вывод
    return {
        "materials": {k: f"{v:,.0f} руб." for k, v in materials_cost.items()},
        "works": {k: f"{v:,.0f} руб." for k, v in works_cost.items()},
        "total_cost": f"{total_cost:,.0f} руб."
    }

def calculate_materials_cost(basic_dims, wall_thickness, profile_id="kp1"):
    """
    Расчет стоимости материалов с учетом профиля КП
    
    Args:
        basic_dims (dict): Словарь с основными размерами
        wall_thickness (float): Толщина стен в мм
        profile_id (str): Идентификатор профиля КП
        
    Returns:
        dict: Словарь с расчетами стоимости материалов
    """
    # Получаем параметры профиля
    profile = get_profile(profile_id)
    
    # Получаем числовые значения из строк
    water_surface = float(basic_dims["Площадь водного зеркала"].split()[0])
    wall_area = float(basic_dims["Площадь стен"].split()[0])
    finishing_area = float(basic_dims["Площадь под отделку"].split()[0])
    concrete_volume = float(basic_dims["Объем бетона"].split()[0])
    
    # Получаем цены из профиля
    prices = profile["materials_prices"]
    
    # Расчет стоимости материалов
    materials_cost = {
        "Бетон": concrete_volume * prices["concrete"],
        "Арматура": concrete_volume * 0.1 * prices["rebar"],  # Примерно 10% от объема бетона
        "ПВХ пленка": water_surface * prices["pvc_film"],
        "Плитка": finishing_area * prices["tile"],
        "Затирка": finishing_area * prices["grout"],
        "Гидроизоляция": finishing_area * prices["waterproofing"],
        "Клей для плитки": finishing_area * prices["tile_adhesive"]
    }
    
    # Общая стоимость материалов
    total_cost = sum(materials_cost.values())
    
    # Форматируем вывод
    return {
        "materials": {k: f"{v:,.0f} руб." for k, v in materials_cost.items()},
        "total_cost": f"{total_cost:,.0f} руб."
    }

def calculate_works_cost(basic_dims, wall_thickness, profile_id="kp1"):
    """
    Расчет стоимости работ с учетом профиля КП
    
    Args:
        basic_dims (dict): Словарь с основными размерами
        wall_thickness (float): Толщина стен в мм
        profile_id (str): Идентификатор профиля КП
        
    Returns:
        dict: Словарь с расчетами стоимости работ
    """
    # Получаем параметры профиля
    profile = get_profile(profile_id)
    
    # Получаем числовые значения из строк
    earth_volume = float(basic_dims["Объем земляных работ"].split()[0])
    concrete_volume = float(basic_dims["Объем бетона"].split()[0])
    finishing_area = float(basic_dims["Площадь под отделку"].split()[0])
    
    # Получаем цены из профиля
    prices = profile["works_prices"]
    
    # Расчет стоимости работ
    works_cost = {
        "Земляные работы": earth_volume * prices["earthworks"],
        "Бетонные работы": concrete_volume * prices["concrete_works"],
        "Армирование": concrete_volume * 0.1 * prices["reinforcement"],  # Примерно 10% от объема бетона
        "Гидроизоляция": finishing_area * prices["waterproofing"],
        "Укладка плитки": finishing_area * prices["tile_laying"],
        "Затирка швов": finishing_area * prices["grouting"],
        "Монтаж оборудования": prices["equipment_installation"],
        "Пусконаладочные работы": prices["commissioning"]
    }
    
    # Общая стоимость работ
    total_cost = sum(works_cost.values())
    
    # Форматируем вывод
    return {
        "works": {k: f"{v:,.0f} руб." for k, v in works_cost.items()},
        "total_cost": f"{total_cost:,.0f} руб."
    }

def calculate_fixed_services():
    """Расчет фиксированных услуг"""
    return {
        "Геодезическая разметка": "15000 ₽",
        "Устройство заземления": "25000 ₽",
        "Работа трактора": "12000 ₽/час",
        "Разгрузка материалов": "15000 ₽",
        "Вызов геодезиста": "8000 ₽",
        "Доставка материалов": "25000 ₽"
    }

def calculate_materials(length, width, depth, wall_thickness):
    """Расчет необходимых материалов"""
    # Переводим в метры
    l, w, d = length/1000, width/1000, depth/1000
    wt = wall_thickness/1000
    
    # Объем бетона М300 для чаши (в м³)
    # Наружные размеры дна
    outer_length = l + 2*wt
    outer_width = w + 2*wt
    bottom_concrete = outer_length * outer_width * wt
    
    # Стены - учитываем 2 стены по наружным размерам
    wall_length = (2 * (outer_length + outer_width)) * d * wt
    
    # Бортики
    border_height = 0.15  # высота бортика 150мм
    border_width = 0.3   # ширина бортика 300мм
    border_length = (outer_length + outer_width) * 2
    border_volume = border_length * border_height * border_width
    
    total_concrete_m300 = bottom_concrete + wall_length + border_volume
    
    # Бетон М200 для подбетонки (в м³)
    base_concrete_thickness = 0.1  # 10 см
    base_concrete = (outer_length + 1.2) * (outer_width + 1.2) * base_concrete_thickness  # +600мм с каждой стороны
    
    # Арматура (в тоннах)
    # Площадь армирования - дно + стены с двойным каркасом
    rebar_bottom = outer_length * outer_width
    rebar_walls = (2 * (outer_length + outer_width)) * (d + border_height)
    total_rebar_area = rebar_bottom + rebar_walls
    rebar_weight = (total_rebar_area * 50) / 1000  # 50 кг/м² при двойном армировании
    
    # Фанера (в листах)
    formwork_area = total_rebar_area * 1.2  # +20% на распил
    sheet_area = 1.52 * 1.52  # размер листа 1520x1520
    plywood_sheets = math.ceil(formwork_area / sheet_area)
    
    return {
        "Бетон M200 (подбетонка)": f"{base_concrete:.1f} м³",
        "Бетон М300 (чаша)": f"{total_concrete_m300:.1f} м³",
        "Общий объем бетона": f"{base_concrete + total_concrete_m300:.1f} м³",
        "Арматура": f"{rebar_weight:.1f} тонн",
        "Количество фанеры": f"{plywood_sheets} листов",
        "Площадь опалубки": f"{formwork_area:.1f} м²"
    }

def calculate_costs(basic_dims, materials):
    """Расчет стоимости на основе КП"""
    costs = {
        "Работы": {
            "Разметка и подготовка": 9600,
            "Земляные работы": 21000,
            "Бетонные работы": 98250,
            "Отделочные работы": 26130,
            "Монтаж оборудования": 115000
        },
        "Материалы": {
            "Бетон М200": float(materials["Бетон M200 (подбетонка)"].split()[0]) * 4350,
            "Бетон М300": float(materials["Бетон М300 (чаша)"].split()[0]) * 5500,
            "Арматура": float(materials["Арматура"].split()[0]) * 54500,
            "Фанера": int(materials["Количество фанеры"].split()[0]) * 1730,
            "Прочие материалы": 35000
        },
        "Оборудование": {
            "Фильтрация": 38208,
            "Освещение": 26376,
            "Автоматика": 30000,
            "Монтаж": 115000
        }
    }
    
    total_works = sum(costs["Работы"].values())
    total_materials = sum(costs["Материалы"].values())
    total_equipment = sum(costs["Оборудование"].values())
    
    return {
        "Работы": costs["Работы"],
        "Материалы": costs["Материалы"],
        "Оборудование": costs["Оборудование"],
        "Итого работы": total_works,
        "Итого материалы": total_materials,
        "Итого оборудование": total_equipment,
        "ИТОГО": total_works + total_materials + total_equipment
    }

def calculate_fixed_values():
    """Возвращает фиксированные значения из КП"""
    return {
        "basic_dimensions": {
            "Площадь водной поверхности": "32.0 м²",
            "Периметр": "24.0 м/п",
            "Площадь стен": "39.6 м²",
            "Площадь под отделку": "71.6 м²",
            "Объем воды": "47.5 м³"
        },
        "earthworks": {
            "Глубина котлована": "2.05 м",
            "Длина котлована": "9.60 м",
            "Ширина котлована": "5.60 м",
            "Площадь котлована": "53.8 м²",
            "Объем котлована": "110.2 м³",
            "Объем обратной засыпки": "41.8 м³",
            "Количество КамАЗов": "14"
        },
        "concrete_works": {
            "Щебень": "4.8 м³",
            "Бетон M200 (подбетонка)": "4.8 м³",
            "Бетон М300 (чаша)": "17.0 м³",
            "Общий объем бетона": "21.8 м³"
        },
        "formwork": {
            "Площадь опалубки": "81.8 м²",
            "Количество фанеры": "37 листов",
            "Вес арматуры": "1584 кг"
        },
        "finishing": {
            "area": 71.6,
            "perimeter": 24.0,
            "material_cost": 107400,
            "material_details": {"Лайнер": 107400},
            "coping_stone": {
                "length": 24.0,
                "price": 3500.00,
                "total": 84000
            },
            "work_cost": 143200,
            "total_cost": 334600
        },
        "materials_cost": {
            "materials": {
                "Бетон М200": 24000,
                "Бетон М300": 102000,
                "Щебень": 8640,
                "Арматура": 102960,
                "Фанера": 66600,
                "Гидроизоляция": 85920
            },
            "equipment": {
                "Скиммер": 15000,
                "Форсунки": 12000,
                "Донный слив": 5000,
                "Прожектор": 12000,
                "Закладные": 10000
            },
            "total_materials": 390120,
            "total_equipment": 54000,
            "total": 444120
        },
        "works_cost": {
            "works": {
                "Земляные работы": {
                    "Выемка грунта": 44080,
                    "Обратная засыпка": 12540,
                    "Вывоз грунта": 91000
                },
                "Бетонные работы": {
                    "Бетонирование подбетонки": 3840,
                    "Бетонирование чаши": 20400,
                    "Укладка щебня": 2400
                },
                "Опалубка и армирование": {
                    "Монтаж опалубки": 49080,
                    "Армирование": 25000
                },
                "Отделочные работы": {
                    "Гидроизоляция": 57280,
                    "Финишная отделка": 107400
                }
            },
            "category_totals": {
                "Земляные работы": 147620,
                "Бетонные работы": 26640,
                "Опалубка и армирование": 74080,
                "Отделочные работы": 164680
            },
            "total": 413020
        },
        "total_cost": 2899664  # Фиксированная итоговая стоимость из КП
    }

def calculate_kp_items(length, width, depth, pool_type):
    """Расчет позиций для коммерческого предложения в формате ООО "ДОН БАСС" """
    
    # Используем те же наименования, что в КП ООО "ДОН БАСС"
    # Оборудование
    equipment_items = [
        {
            "name": "Фильтрационная установка Hayward PWL D611 81073 (14m3/h, верх)",
            "unit": "шт.",
            "qty": 1,
            "price": 79975.00
        },
        {
            "name": "Скиммер под лайнер Aquaviva Wide EM0020V",
            "unit": "шт.",
            "qty": 2,
            "price": 9115.00
        },
        {
            "name": "Форсунка стеновая под лайнер Aquaviva EM4414 (50 мм/2\" сопло \"круг\", латунные вставки",
            "unit": "шт.",
            "qty": 4,
            "price": 1979.00
        },
        {
            "name": "Слив донный под лайнер Aquaviva EM2837",
            "unit": "шт.",
            "qty": 1,
            "price": 4727.00
        },
        {
            "name": "Прожектор светодиодный Aquaviva LED003 546LED (36 Вт) White",
            "unit": "шт.",
            "qty": 2,
            "price": 26129.00
        },
        {
            "name": "Трансформатор Aquant 105 Вт-12В",
            "unit": "шт.",
            "qty": 1,
            "price": 6256.00
        },
        {
            "name": "Дозовая коробка Aquaviva EM2823",
            "unit": "шт.",
            "qty": 2,
            "price": 1078.00
        },
        {
            "name": "Песок кварцевый 25кг Aquaviva 0,5-0,8 мм",
            "unit": "шт.",
            "qty": 6,
            "price": 1152.00
        },
        {
            "name": "Набор химии для запуска бассейна",
            "unit": "компл",
            "qty": 1,
            "price": 12318.00
        },
        {
            "name": "Набор для ухода за бассейном",
            "unit": "компл",
            "qty": 1,
            "price": 17580.00
        },
        {
            "name": "Инсталляция ( трубы, краны, фитинги )",
            "unit": "компл",
            "qty": 1,
            "price": 102000.00
        },
        {
            "name": "Щит Электра контроля",
            "unit": "компл",
            "qty": 1,
            "price": 48000.00
        },
        {
            "name": "Монтаж и наладка оборудования, запуск",
            "unit": "услуга",
            "qty": 1,
            "price": 186000.00
        }
    ]
    
    # Добавляем лайнер или другую отделку в зависимости от типа бассейна
    if pool_type == "liner":
        equipment_items.append({
            "name": "Лайнер Cefil Urdike (синий) , геотекстиль , клей , крепление , работа",
            "unit": "м2",
            "qty": 90,
            "price": 5400.00
        })
    elif pool_type == "tile":
        equipment_items.append({
            "name": "Плитка для бассейна, клей, затирка, работа",
            "unit": "м2",
            "qty": 90,
            "price": 8900.00
        })
    else:  # mosaic
        equipment_items.append({
            "name": "Мозаика для бассейна, клей, затирка, работа",
            "unit": "м2",
            "qty": 90,
            "price": 12300.00
        })
    
    # Добавляем копинговый камень
    equipment_items.append({
        "name": "Копинговый камень",
        "unit": "шт.",
        "qty": 46,
        "price": 2600.00
    })
    
    # Расчет общей стоимости оборудования
    equipment_total = sum(item["qty"] * item["price"] for item in equipment_items)
    
    # Материалы
    materials_items = [
        {
            "name": "Выемка грунта под бассейн механизированным способом",
            "unit": "м3",
            "qty": 122,
            "price": 400.00
        },
        {
            "name": "Вывоз чистого грунта с территории участка",
            "unit": "КамАЗ",
            "qty": 15,
            "price": 6500.00
        },
        {
            "name": "Песок по факту с доставкой 6 м3",
            "unit": "шт.",
            "qty": 1,
            "price": 7600.00
        },
        {
            "name": "Щебень по факту с доставкой 10 т",
            "unit": "шт.",
            "qty": 1,
            "price": 9700.00
        },
        {
            "name": "Фанера 1520/1520/18",
            "unit": "лист",
            "qty": 48,
            "price": 1900.00
        },
        {
            "name": "Арматура d-12",
            "unit": "т",
            "qty": 1.8,
            "price": 65000.00
        },
        {
            "name": "Брус 50/50",
            "unit": "м/п",
            "qty": 130,
            "price": 90.00
        },
        {
            "name": "Брус 100/50",
            "unit": "м/п",
            "qty": 320,
            "price": 130.00
        },
        {
            "name": "Тяжи, проволока вязальная, диски по металлу, саморезы , труба квадрат , буры , диск по дереву и т д",
            "unit": "компл.",
            "qty": 1,
            "price": 60000.00
        },
        {
            "name": "Бетон М-200 с доставкой",
            "unit": "м3",
            "qty": 5,
            "price": 5750.00
        },
        {
            "name": "Бетон М-300 с доставкой",
            "unit": "м3",
            "qty": 20,
            "price": 6650.00
        },
        {
            "name": "Уголок на заземление",
            "unit": "компл.",
            "qty": 1,
            "price": 8000.00
        },
        {
            "name": "Бетононасос",
            "unit": "услуга",
            "qty": 1,
            "price": 44000.00
        },
        {
            "name": "Блок газобетонный Hebel D500 625x250x250 мм",
            "unit": "шт.",
            "qty": 12,
            "price": 323.00
        },
        {
            "name": "Бетон М200 с доставкой",
            "unit": "м3",
            "qty": 1,
            "price": 8750.00
        },
        {
            "name": "MAPEI MAPEFILL 25кг для закладных деталей",
            "unit": "шт.",
            "qty": 8,
            "price": 1400.00
        },
        {
            "name": "Грунтовка СТ-17",
            "unit": "шт.",
            "qty": 2,
            "price": 1150.00
        },
        {
            "name": "Клей плиточный ЕС-3000",
            "unit": "шт.",
            "qty": 8,
            "price": 465.00
        },
        {
            "name": "Штукатурка фиброармированная высокопрочная",
            "unit": "шт.",
            "qty": 60,
            "price": 670.00
        },
        {
            "name": "Клей к-80",
            "unit": "шт.",
            "qty": 5,
            "price": 1420.00
        },
        {
            "name": "Затирка для копинга",
            "unit": "компл.",
            "qty": 1,
            "price": 4200.00
        },
        {
            "name": "Герметик для копинга",
            "unit": "шт.",
            "qty": 6,
            "price": 1280.00
        },
        {
            "name": "Доставка и покупка материала",
            "unit": "услуга",
            "qty": 1,
            "price": 30000.00
        }
    ]
    
    # Расчет общей стоимости материалов
    materials_total = sum(item["qty"] * item["price"] for item in materials_items)
    
    # Работы
    works_items = [
        {
            "name": "Разметка бассейна для техники, нивелировка, привязка к территории по всем этапам работ",
            "unit": "м2",
            "qty": 58,
            "price": 600.00
        },
        {
            "name": "Работа с трактором",
            "unit": "услуга",
            "qty": 1,
            "price": 15000.00
        },
        {
            "name": "Доработка грунта вручную",
            "unit": "м2",
            "qty": 58,
            "price": 400.00
        },
        {
            "name": "Отсыпка щебнем дна бассейна, трамбовка",
            "unit": "м2",
            "qty": 58,
            "price": 500.00
        },
        {
            "name": "Устройство контур заземления",
            "unit": "шт.",
            "qty": 1,
            "price": 8000.00
        },
        {
            "name": "Бетонирование подбетонки с миксера",
            "unit": "м2",
            "qty": 47,
            "price": 800.00
        },
        {
            "name": "Монтаж наружной опалубки стен для бетонирования стен и дна бассейна монолитом",
            "unit": "м2",
            "qty": 49.4,
            "price": 650.00
        },
        {
            "name": "Армировка двойным каркасом бассейна дно и стены",
            "unit": "м2",
            "qty": 81.4,
            "price": 1750.00
        },
        {
            "name": "Монтаж внутренней опалубки",
            "unit": "м2",
            "qty": 39.6,
            "price": 750.00
        },
        {
            "name": "Изготовление проемов под закладные детали",
            "unit": "шт.",
            "qty": 9,
            "price": 1500.00
        },
        {
            "name": "Бетонирование бассейна монолитом дно и стены",
            "unit": "м3",
            "qty": 20,
            "price": 7000.00
        },
        {
            "name": "Демонтаж опалубки",
            "unit": "м2",
            "qty": 89,
            "price": 300.00
        },
        {
            "name": "Изготовление веерных ступеней в бассейне",
            "unit": "шт.",
            "qty": 5,
            "price": 12000.00
        },
        {
            "name": "Монтаж опалубки, бетонирование закладных деталей оборудования",
            "unit": "шт.",
            "qty": 9,
            "price": 3000.00
        },
        {
            "name": "Обратная отсыпка чаши бассейна глиной или песком с послойным уплотнением",
            "unit": "м3",
            "qty": 30,
            "price": 1200.00
        },
        {
            "name": "Отсыпка коммуникаций бассейна песком",
            "unit": "м/п",
            "qty": 32,
            "price": 450.00
        },
        {
            "name": "Грунтовка бассейна под штукатурку",
            "unit": "м2",
            "qty": 71.6,
            "price": 100.00
        },
        {
            "name": "Нанесение клея под гребенку для улучшения адгезии",
            "unit": "м2",
            "qty": 71.6,
            "price": 300.00
        },
        {
            "name": "Маячная штукатурка бассейна цементно песчаным раствором",
            "unit": "м2",
            "qty": 71.6,
            "price": 1000.00
        },
        {
            "name": "Грунтовка борта бассейна под штукатурку",
            "unit": "м/п",
            "qty": 26,
            "price": 100.00
        },
        {
            "name": "Нанесение клея под гребенку для улучшения адгезии",
            "unit": "м/п",
            "qty": 26,
            "price": 300.00
        },
        {
            "name": "Штукатурка борта бассейна",
            "unit": "м/п",
            "qty": 26,
            "price": 1000.00
        },
        {
            "name": "Грунтовка ступеней бассейна под штукатурку",
            "unit": "м/п",
            "qty": 14,
            "price": 100.00
        },
        {
            "name": "Нанесение клея под гребенку для улучшения адгезии",
            "unit": "м/п",
            "qty": 14,
            "price": 300.00
        },
        {
            "name": "Штукатурка ступеней",
            "unit": "м/п",
            "qty": 14,
            "price": 1000.00
        },
        {
            "name": "Грунтовка бассейна под лайнер",
            "unit": "м2",
            "qty": 71.6,
            "price": 100.00
        },
        {
            "name": "Грунтовка борта, ступеней",
            "unit": "м/п",
            "qty": 40,
            "price": 100.00
        },
        {
            "name": "Монтаж бортового камня на борт бассейна",
            "unit": "м/п",
            "qty": 26,
            "price": 2500.00
        },
        {
            "name": "Разгрузка и подноска строительных материалов",
            "unit": "услуга",
            "qty": 1,
            "price": 30000.00
        }
    ]
    
    # Расчет общей стоимости работ
    works_total = sum(item["qty"] * item["price"] for item in works_items)
    
    return {
        "equipment_items": equipment_items,
        "equipment_total": equipment_total,
        "materials_items": materials_items,
        "materials_total": materials_total,
        "works_items": works_items,
        "works_total": works_total
    }

def num2text(num):
    """Конвертация числа в текстовый формат"""
    units = (
        'ноль', 'один', 'два', 'три', 'четыре', 'пять', 'шесть',
        'семь', 'восемь', 'девять'
    )
    teens = (
        'десять', 'одиннадцать', 'двенадцать', 'тринадцать', 'четырнадцать',
        'пятнадцать', 'шестнадцать', 'семнадцать', 'восемнадцать', 'девятнадцать'
    )
    tens = (
        'двадцать', 'тридцать', 'сорок', 'пятьдесят', 'шестьдесят',
        'семьдесят', 'восемьдесят', 'девяносто'
    )
    hundreds = (
        'сто', 'двести', 'триста', 'четыреста', 'пятьсот', 'шестьсот',
        'семьсот', 'восемьсот', 'девятьсот'
    )
    
    def _convert_group(num):
        s = ''
        if num >= 100:
            s += hundreds[num // 100 - 1] + ' '
            num %= 100
        
        if num >= 20:
            s += tens[num // 10 - 2] + ' '
            num %= 10
        
        if num >= 10:
            s += teens[num - 10] + ' '
        elif num > 0:
            s += units[num] + ' '
            
        return s.strip()
    
    if num == 0:
        return 'ноль рублей ноль копеек'
    
    # Разделяем целую и дробную части
    rub, kop = divmod(round(num * 100), 100)
    
    # Обрабатываем рубли
    text = ''
    if rub > 0:
        for unit_index, unit_name in enumerate(('', 'тысяч', 'миллион', 'миллиард')):
            _num = rub % 1000
            if _num > 0:
                group_text = _convert_group(_num)
                if unit_index > 0:
                    if _num % 10 == 1 and _num % 100 != 11:
                        unit_text = unit_name + 'а'
                    elif 2 <= _num % 10 <= 4 and (_num % 100 < 10 or _num % 100 >= 20):
                        unit_text = unit_name + 'и'
                    else:
                        unit_text = unit_name
                    text = group_text + ' ' + unit_text + ' ' + text
                else:
                    text = group_text + ' ' + text
            rub //= 1000
        
        # Добавляем слово "рублей" с правильным окончанием
        if rub % 10 == 1 and rub % 100 != 11:
            text += 'рубль'
        elif 2 <= rub % 10 <= 4 and (rub % 100 < 10 or rub % 100 >= 20):
            text += 'рубля'
        else:
            text += 'рублей'
    
    # Добавляем копейки
    if kop > 0:
        text += ' ' + str(kop) + ' копеек'
    else:
        text += ' ноль копеек'
    
    return text.capitalize()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/calculate', methods=['POST'])
def calculate_route():
    """
    Маршрут для расчета стоимости бассейна
    
    Ожидает POST-запрос с JSON-данными:
    {
        "length": float,      # Длина бассейна в мм
        "width": float,       # Ширина бассейна в мм
        "depth": float,       # Глубина бассейна в мм
        "wall_thickness": float,  # Толщина стен в мм
        "profile_id": str     # Идентификатор профиля КП (опционально)
    }
    
    Returns:
        JSON с результатами расчета или сообщением об ошибке
    """
    try:
        # Получаем данные из запроса
        data = request.get_json()
        if not data:
            return jsonify({"error": "Не получены данные"}), 400
            
        # Извлекаем параметры
        length = float(data.get("length", 0))
        width = float(data.get("width", 0))
        depth = float(data.get("depth", 0))
        wall_thickness = float(data.get("wall_thickness", 0))
        profile_id = data.get("profile_id", "kp1")
        
        # Проверяем корректность параметров
        if not all(isinstance(x, (int, float)) for x in [length, width, depth, wall_thickness]):
            return jsonify({"error": "Все параметры должны быть числами"}), 400
            
        if not all(x > 0 for x in [length, width, depth, wall_thickness]):
            return jsonify({"error": "Все параметры должны быть положительными числами"}), 400
            
        # Проверяем корректность профиля
        if profile_id not in PROFILES:
            return jsonify({"error": f"Неизвестный профиль КП: {profile_id}"}), 400
        
        # Выполняем расчет
        result = calculate(length, width, depth, wall_thickness, profile_id)
        
        if "error" in result:
            return jsonify({"error": result["error"]}), 400
            
        return jsonify(result)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/compare_estimate', methods=['POST'])
def compare_estimate():
    """
    Маршрут для сравнения расчета с предоставленной сметой
    
    Ожидает POST-запрос с JSON-данными:
    {
        "length": float,      # Длина бассейна в мм
        "width": float,       # Ширина бассейна в мм
        "depth": float,       # Глубина бассейна в мм
        "wall_thickness": float,  # Толщина стен в мм
        "profile_id": str,    # Идентификатор профиля КП
        "estimate": {         # Данные сметы для сравнения
            "water_surface": float,  # Площадь водного зеркала в м²
            "perimeter": float,      # Периметр в м
            "wall_area": float,      # Площадь стен в м²
            "finishing_area": float, # Площадь под отделку в м²
            "water_volume": float,   # Объем воды в м³
            "total_cost": float      # Общая стоимость в руб.
        }
    }
    
    Returns:
        JSON с результатами сравнения или сообщением об ошибке
    """
    try:
        # Получаем данные из запроса
        data = request.get_json()
        if not data:
            return jsonify({"error": "Не получены данные"}), 400
            
        # Извлекаем параметры
        length = float(data.get("length", 0))
        width = float(data.get("width", 0))
        depth = float(data.get("depth", 0))
        wall_thickness = float(data.get("wall_thickness", 0))
        profile_id = data.get("profile_id", "kp1")
        estimate = data.get("estimate", {})
        
        # Проверяем корректность параметров
        if not all(isinstance(x, (int, float)) for x in [length, width, depth, wall_thickness]):
            return jsonify({"error": "Все параметры должны быть числами"}), 400
            
        if not all(x > 0 for x in [length, width, depth, wall_thickness]):
            return jsonify({"error": "Все параметры должны быть положительными числами"}), 400
            
        # Проверяем корректность профиля
        if profile_id not in PROFILES:
            return jsonify({"error": f"Неизвестный профиль КП: {profile_id}"}), 400
            
        # Проверяем наличие обязательных данных сметы
        required_estimate_fields = ["water_surface", "perimeter", "wall_area", "finishing_area", "water_volume", "total_cost"]
        missing_fields = [field for field in required_estimate_fields if field not in estimate]
        if missing_fields:
            return jsonify({"error": f"Отсутствуют обязательные данные сметы: {', '.join(missing_fields)}"}), 400
        
        # Выполняем расчет
        result = calculate(length, width, depth, wall_thickness, profile_id)
        
        if "error" in result:
            return jsonify({"error": result["error"]}), 400
            
        # Извлекаем числовые значения из результата
        calculated = {
            "water_surface": float(result["basic_dimensions"]["Площадь водного зеркала"].split()[0]),
            "perimeter": float(result["basic_dimensions"]["Периметр"].split()[0]),
            "wall_area": float(result["basic_dimensions"]["Площадь стен"].split()[0]),
            "finishing_area": float(result["basic_dimensions"]["Площадь под отделку"].split()[0]),
            "water_volume": float(result["basic_dimensions"]["Объем воды"].split()[0]),
            "total_cost": float(result["total_cost"].replace(" руб.", "").replace(",", ""))
        }
        
        # Рассчитываем отклонения
        deviations = {}
        for field in required_estimate_fields:
            if calculated[field] != 0:
                deviation = ((estimate[field] - calculated[field]) / calculated[field]) * 100
                deviations[field] = {
                    "calculated": calculated[field],
                    "estimated": estimate[field],
                    "deviation": f"{deviation:.1f}%"
                }
        
        return jsonify({
            "calculated": calculated,
            "estimated": estimate,
            "deviations": deviations,
            "profile": PROFILES[profile_id]["name"]
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/generate_kp', methods=['POST'])
def generate_kp():
    """
    Маршрут для генерации коммерческого предложения
    
    Ожидает POST-запрос с JSON-данными:
    {
        "length": float,      # Длина бассейна в мм
        "width": float,       # Ширина бассейна в мм
        "depth": float,       # Глубина бассейна в мм
        "wall_thickness": float,  # Толщина стен в мм
        "profile_id": str,    # Идентификатор профиля КП
        "customer": {         # Данные заказчика
            "name": str,
            "address": str,
            "phone": str,
            "email": str
        }
    }
    
    Returns:
        JSON с результатами расчета или сообщением об ошибке
    """
    try:
        # Получаем данные из запроса
        data = request.get_json()
        if not data:
            return jsonify({"error": "Не получены данные"}), 400
            
        # Извлекаем параметры
        length = float(data.get("length", 0))
        width = float(data.get("width", 0))
        depth = float(data.get("depth", 0))
        wall_thickness = float(data.get("wall_thickness", 0))
        profile_id = data.get("profile_id", "kp1")
        customer = data.get("customer", {})
        
        # Проверяем корректность параметров
        if not all(isinstance(x, (int, float)) for x in [length, width, depth, wall_thickness]):
            return jsonify({"error": "Все параметры должны быть числами"}), 400
            
        if not all(x > 0 for x in [length, width, depth, wall_thickness]):
            return jsonify({"error": "Все параметры должны быть положительными числами"}), 400
            
        # Проверяем корректность профиля
        if profile_id not in PROFILES:
            return jsonify({"error": f"Неизвестный профиль КП: {profile_id}"}), 400
            
        # Проверяем наличие обязательных данных заказчика
        required_customer_fields = ["name", "address", "phone"]
        missing_fields = [field for field in required_customer_fields if field not in customer]
        if missing_fields:
            return jsonify({"error": f"Отсутствуют обязательные данные заказчика: {', '.join(missing_fields)}"}), 400
        
        # Выполняем расчет
        result = calculate(length, width, depth, wall_thickness, profile_id)
        
        if "error" in result:
            return jsonify({"error": result["error"]}), 400
            
        # Добавляем данные заказчика
        result["customer"] = customer
        
        # Добавляем дату генерации КП
        result["generation_date"] = datetime.now().strftime("%d.%m.%Y")
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/get_profiles', methods=['GET'])
def get_profiles():
    """
    Маршрут для получения списка доступных профилей КП
    
    Returns:
        JSON со списком профилей КП
    """
    try:
        profiles = get_profiles_list()
        return jsonify({
            "profiles": profiles
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/get_profile/<profile_id>', methods=['GET'])
def get_profile_route(profile_id):
    """
    Маршрут для получения параметров конкретного профиля КП
    
    Args:
        profile_id (str): Идентификатор профиля КП
        
    Returns:
        JSON с параметрами профиля КП или сообщением об ошибке
    """
    try:
        # Проверяем корректность профиля
        if profile_id not in PROFILES:
            return jsonify({"error": f"Неизвестный профиль КП: {profile_id}"}), 400
            
        # Получаем параметры профиля
        profile = get_profile(profile_id)
        
        return jsonify({
            "profile": profile
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/get_dimensions_correction', methods=['POST'])
def get_dimensions_correction():
    """
    Маршрут для получения коэффициентов корректировки размеров
    
    Ожидает POST-запрос с JSON-данными:
    {
        "length": float,      # Длина бассейна в мм
        "width": float,       # Ширина бассейна в мм
        "depth": float,       # Глубина бассейна в мм
        "profile_id": str     # Идентификатор профиля КП
    }
    
    Returns:
        JSON с коэффициентами корректировки или сообщением об ошибке
    """
    try:
        # Получаем данные из запроса
        data = request.get_json()
        if not data:
            return jsonify({"error": "Не получены данные"}), 400
            
        # Извлекаем параметры
        length = float(data.get("length", 0))
        width = float(data.get("width", 0))
        depth = float(data.get("depth", 0))
        profile_id = data.get("profile_id", "kp1")
        
        # Проверяем корректность параметров
        if not all(isinstance(x, (int, float)) for x in [length, width, depth]):
            return jsonify({"error": "Все параметры должны быть числами"}), 400
            
        if not all(x > 0 for x in [length, width, depth]):
            return jsonify({"error": "Все параметры должны быть положительными числами"}), 400
            
        # Проверяем корректность профиля
        if profile_id not in PROFILES:
            return jsonify({"error": f"Неизвестный профиль КП: {profile_id}"}), 400
            
        # Получаем коэффициенты корректировки
        correction_factors = get_dimensions_correction_factor(profile_id, {
            "length": length,
            "width": width,
            "depth": depth
        })
        
        return jsonify({
            "correction_factors": correction_factors,
            "profile": PROFILES[profile_id]["name"]
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/get_prices', methods=['POST'])
def get_prices():
    """
    Маршрут для получения цен из профиля КП
    
    Ожидает POST-запрос с JSON-данными:
    {
        "profile_id": str     # Идентификатор профиля КП
    }
    
    Returns:
        JSON с ценами материалов и работ или сообщением об ошибке
    """
    try:
        # Получаем данные из запроса
        data = request.get_json()
        if not data:
            return jsonify({"error": "Не получены данные"}), 400
            
        # Извлекаем параметры
        profile_id = data.get("profile_id", "kp1")
        
        # Проверяем корректность профиля
        if profile_id not in PROFILES:
            return jsonify({"error": f"Неизвестный профиль КП: {profile_id}"}), 400
            
        # Получаем профиль
        profile = get_profile(profile_id)
        
        return jsonify({
            "materials_prices": profile["materials_prices"],
            "works_prices": profile["works_prices"],
            "profile": profile["name"]
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/get_costs', methods=['POST'])
def get_costs():
    """
    Маршрут для получения стоимостей из профиля КП
    
    Ожидает POST-запрос с JSON-данными:
    {
        "profile_id": str     # Идентификатор профиля КП
    }
    
    Returns:
        JSON со стоимостями материалов, работ и оборудования или сообщением об ошибке
    """
    try:
        # Получаем данные из запроса
        data = request.get_json()
        if not data:
            return jsonify({"error": "Не получены данные"}), 400
            
        # Извлекаем параметры
        profile_id = data.get("profile_id", "kp1")
        
        # Проверяем корректность профиля
        if profile_id not in PROFILES:
            return jsonify({"error": f"Неизвестный профиль КП: {profile_id}"}), 400
            
        # Получаем профиль
        profile = get_profile(profile_id)
        
        return jsonify({
            "costs": profile["costs"],
            "profile": profile["name"]
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 400

def calculate(length, width, depth, wall_thickness, profile_id="kp1"):
    """
    Расчет стоимости бассейна с учетом профиля КП
    
    Args:
        length (float): Длина бассейна в мм
        width (float): Ширина бассейна в мм
        depth (float): Глубина бассейна в мм
        wall_thickness (float): Толщина стен в мм
        profile_id (str): Идентификатор профиля КП
        
    Returns:
        dict: Словарь с результатами расчета
    """
    try:
        # Получаем параметры профиля
        profile = get_profile(profile_id)
        
        # Расчет основных размеров
        basic_dims = calculate_basic_dimensions(length, width, depth, wall_thickness, profile_id)
        
        # Расчет стоимости материалов
        materials_cost = calculate_materials_cost(basic_dims, wall_thickness, profile_id)
        
        # Расчет стоимости работ
        works_cost = calculate_works_cost(basic_dims, wall_thickness, profile_id)
        
        # Расчет стоимости отделочных работ
        finishing_cost = calculate_finishing_cost(basic_dims, profile_id)
        
        # Получаем числовые значения стоимости
        materials_total = 0
        if isinstance(materials_cost["total_cost"], (int, float)):
            materials_total = materials_cost["total_cost"]
        else:
            # Пытаемся извлечь числовое значение из строки
            try:
                materials_total = float(str(materials_cost["total_cost"]).replace(" руб.", "").replace(",", ""))
            except:
                materials_total = 0
                
        works_total = 0
        if isinstance(works_cost["total_cost"], (int, float)):
            works_total = works_cost["total_cost"]
        else:
            # Пытаемся извлечь числовое значение из строки
            try:
                works_total = float(str(works_cost["total_cost"]).replace(" руб.", "").replace(",", ""))
            except:
                works_total = 0
                
        finishing_total = 0
        if isinstance(finishing_cost["total_cost"], (int, float)):
            finishing_total = finishing_cost["total_cost"]
        else:
            # Пытаемся извлечь числовое значение из строки
            try:
                finishing_total = float(str(finishing_cost["total_cost"]).replace(" руб.", "").replace(",", ""))
            except:
                finishing_total = 0
        
        # Общая стоимость
        total_cost = materials_total + works_total + finishing_total
        
        # Форматируем результат
        result = {
            "basic_dimensions": basic_dims,
            "materials_cost": materials_cost,
            "works_cost": works_cost,
            "finishing_cost": finishing_cost,
            "total_cost": f"{total_cost:,.0f} руб.",
            "profile": profile["name"]
        }
        
        return result
        
    except Exception as e:
        return {"error": str(e)}

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 3333))
    app.run(host='0.0.0.0', port=port, debug=True) 