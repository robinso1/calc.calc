from flask import Flask, render_template, request, jsonify, redirect, url_for, send_file
import os
import math
import json
import logging
from flask_cors import CORS
from datetime import datetime
from kp_profiles import get_profile, get_profiles_list, get_dimensions_correction_factor
from io import BytesIO
import traceback

app = Flask(__name__, template_folder="templates")
CORS(app, resources={r"/*": {"origins": "*"}})
app.logger.setLevel(logging.DEBUG)

@app.before_request
def log_request_info():
    app.logger.debug('Headers: %s', request.headers)
    app.logger.debug('Body: %s', request.get_data())

@app.after_request
def after_request(response):
    # Добавляем заголовки CORS для всех запросов
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add("Access-Control-Allow-Headers", "Content-Type,Authorization")
    response.headers.add("Access-Control-Allow-Methods", "GET,PUT,POST,DELETE,OPTIONS")
    app.logger.debug('Response status: %s', response.status)
    app.logger.debug('Response Content-Type: %s', response.content_type)
    return response

def calculate_basic_dimensions(length, width, depth, wall_thickness, correction_factors=None):
    """
    Расчет основных размеров бассейна с учетом профиля КП
    
    Args:
        length (float): Длина бассейна в мм (внутренний размер)
        width (float): Ширина бассейна в мм (внутренний размер)
        depth (float): Глубина бассейна в мм (внутренний размер)
        wall_thickness (float): Толщина стен и дна в мм
        correction_factors (dict): Коэффициенты корректировки размеров
        
    Returns:
        dict: Словарь с основными размерами
    """
    
    # Конвертируем размеры в метры
    length_m = length / 1000  # Внутренняя длина в метрах
    width_m = width / 1000    # Внутренняя ширина в метрах
    depth_m = depth / 1000    # Внутренняя глубина в метрах
    wall_thickness_m = wall_thickness / 1000  # Толщина стен в метрах
    
    # Наружные размеры бассейна (внутренние + толщина стен с каждой стороны)
    outer_length_m = length_m + (2 * wall_thickness_m)
    outer_width_m = width_m + (2 * wall_thickness_m)
    
    # Периметр по внутренним размерам
    inner_perimeter = 2 * (length_m + width_m)
    
    # Периметр по наружным размерам
    outer_perimeter = 2 * (outer_length_m + outer_width_m)
    
    # Расчет площади водного зеркала (площадь дна по внутренним размерам)
    water_surface = length_m * width_m
    
    # Расчет площади стен (периметр по внутренним размерам умноженный на глубину)
    wall_area = inner_perimeter * depth_m
    
    # Расчет общей площади под отделку (дно + стены)
    finishing_area = water_surface + wall_area
    
    # Расчет объема воды
    water_volume = water_surface * depth_m
    
    # Наружные размеры дна
    outer_bottom_area = outer_length_m * outer_width_m
    
    # Объем бетона дна
    bottom_concrete_volume = outer_bottom_area * wall_thickness_m
    
    # Объем бетона стен (периметр внутренний * высоту * толщину)
    walls_concrete_volume = inner_perimeter * depth_m * wall_thickness_m
    
    # Общий объем бетона
    concrete_volume = bottom_concrete_volume + walls_concrete_volume
    
    # Расчет объема земляных работ
    # Размеры котлована с запасом 800 мм с каждой стороны от внутреннего размера
    pit_length = length_m + 2 * (wall_thickness_m + 0.55)  # +550 мм с каждой стороны для работы
    pit_width = width_m + 2 * (wall_thickness_m + 0.55)   # +550 мм с каждой стороны для работы
    pit_area = pit_length * pit_width
    
    # Глубина котлована: внутренняя глубина + толщина дна + 200 мм (щебень 100 + подбетонка 100)
    pit_depth = depth_m + wall_thickness_m + 0.2
    
    # Объем земляных работ
    earth_volume = pit_area * pit_depth
    
    # Проверяем, переданы ли коэффициенты корректировки
    if correction_factors is None:
        # Если не переданы, используем стандартные значения (без корректировки)
        correction_factors = {
            "water_surface": 1.0,
            "perimeter": 1.0,
            "wall_area": 1.0,
            "finishing_area": 1.0,
            "water_volume": 1.0
        }
    
    # Применяем корректировку к рассчитанным значениям
    water_surface = water_surface * correction_factors.get("water_surface", 1.0)
    inner_perimeter = inner_perimeter * correction_factors.get("perimeter", 1.0)
    wall_area = wall_area * correction_factors.get("wall_area", 1.0)
    finishing_area = finishing_area * correction_factors.get("finishing_area", 1.0)
    water_volume = water_volume * correction_factors.get("water_volume", 1.0)
    
    # Создаем словарь с "сырыми" числовыми значениями для использования в других функциях
    raw_dims = {
        "water_surface": water_surface,
        "perimeter": inner_perimeter,
        "wall_area": wall_area,
        "finishing_area": finishing_area,
        "water_volume": water_volume,
        "concrete_volume": concrete_volume,
        "earth_volume": earth_volume,
        "outer_length": outer_length_m,
        "outer_width": outer_width_m,
        "outer_perimeter": outer_perimeter,
        "pit_area": pit_area,
        "pit_length": pit_length,
        "pit_width": pit_width,
        "pit_depth": pit_depth
    }
    
    # Возвращаем словарь с форматированными и сырыми значениями
    return {
        "Глубина": f"{depth_m * 1000:.0f} мм",
        "Длина внутренняя": f"{length_m * 1000:.0f} мм",
        "Ширина внутренняя": f"{width_m * 1000:.0f} мм",
        "Площадь водного зеркала": f"{water_surface:.1f} м²",
        "Периметр": f"{inner_perimeter:.1f} м/п",
        "Площадь стен": f"{wall_area:.1f} м²",
        "Площадь отделки": f"{finishing_area:.1f} м²",
        "Объем воды": f"{water_volume:.1f} м³",
        "Объем бетона": f"{concrete_volume:.1f} м³",
        "Объем земляных работ": f"{earth_volume:.1f} м³",
        "Общая площадь": f"{finishing_area:.1f} м²",
        "_raw": raw_dims  # Включаем сырые данные для использования в других функциях
    }

def calculate_earthworks(length, width, depth, wall_thickness):
    """
    Расчет земляных работ
    
    Args:
        length (float): Длина бассейна в мм (внутренний размер)
        width (float): Ширина бассейна в мм (внутренний размер)
        depth (float): Глубина бассейна в мм (внутренний размер)
        wall_thickness (float): Толщина стен и дна в мм
        
    Returns:
        dict: Словарь с результатами расчета
    """
    # Конвертируем размеры в метры
    length_m = length / 1000
    width_m = width / 1000
    depth_m = depth / 1000
    wall_thickness_m = wall_thickness / 1000
    
    # Размеры котлована (внутренние размеры + толщина стен + 800мм с каждой стороны)
    pit_length = length_m + 2 * (wall_thickness_m + 0.8)  # +800 мм с каждой стороны для работы
    pit_width = width_m + 2 * (wall_thickness_m + 0.8)    # +800 мм с каждой стороны для работы
    pit_area = pit_length * pit_width
    
    # Глубина котлована: внутренняя глубина + толщина дна + 200мм (щебень + подбетонка)
    pit_depth = depth_m + wall_thickness_m + 0.2
    
    # Объем земляных работ
    pit_volume = pit_area * pit_depth
    
    # Объем обратной засыпки (объем котлована минус объем бассейна с учетом стен)
    outer_length = length_m + 2 * wall_thickness_m
    outer_width = width_m + 2 * wall_thickness_m
    outer_depth = depth_m + wall_thickness_m
    pool_volume = outer_length * outer_width * outer_depth
    
    # Объем пространства между бассейном и краем котлована
    backfill_volume = pit_volume - pool_volume
    
    # Объем вывоза (общий объем котлована минус объем обратной засыпки)
    removal_volume = pit_volume
    
    # Количество КАМАЗов (1 КАМАЗ ~ 7 м³)
    trucks_count = math.ceil(removal_volume / 7)
    
    return {
        "Глубина котлована": f"{pit_depth * 1000:.0f} мм",
        "Длина котлована": f"{pit_length * 1000:.0f} мм",
        "Ширина котлована": f"{pit_width * 1000:.0f} мм",
        "Площадь котлована": f"{pit_area:.1f} м²",
        "Объем земляных работ": f"{pit_volume:.1f} м³",
        "Объем обратной засыпки": f"{backfill_volume:.1f} м³",
        "Объем вывоза грунта": f"{removal_volume:.1f} м³",
        "Количество КАМАЗов": f"{trucks_count}"
    }

def calculate_concrete_works(length, width, depth, wall_thickness):
    """
    Расчет бетонных работ
    
    Args:
        length (float): Длина бассейна в мм (внутренний размер)
        width (float): Ширина бассейна в мм (внутренний размер)
        depth (float): Глубина бассейна в мм (внутренний размер)
        wall_thickness (float): Толщина стен и дна в мм
        
    Returns:
        dict: Словарь с результатами расчета
    """
    # Конвертируем размеры в метры
    length_m = length / 1000
    width_m = width / 1000
    depth_m = depth / 1000
    wall_thickness_m = wall_thickness / 1000
    
    # Наружные размеры бассейна
    outer_length = length_m + 2 * wall_thickness_m
    outer_width = width_m + 2 * wall_thickness_m
    
    # Площадь основания (по наружным размерам)
    base_area = outer_length * outer_width
    
    # Объем бетона для основания
    base_concrete_volume = base_area * wall_thickness_m
    
    # Периметр внутренний
    inner_perimeter = 2 * (length_m + width_m)
    
    # Объем бетона для стен
    walls_concrete_volume = inner_perimeter * depth_m * wall_thickness_m
    
    # Общий объем бетона
    total_concrete_volume = base_concrete_volume + walls_concrete_volume
    
    # Объем щебня (100 мм под всем основанием)
    gravel_thickness = 0.1  # 100 мм в метрах
    gravel_volume = base_area * gravel_thickness
    
    # Вес арматуры (примерно 100 кг на 1 м³ бетона)
    reinforcement_weight = total_concrete_volume * 100  # кг
    
    return {
        "Объем щебня": f"{gravel_volume:.1f} м³",
        "Объем бетона основания": f"{base_concrete_volume:.1f} м³",
        "Объем бетона стен": f"{walls_concrete_volume:.1f} м³",
        "Общий объем бетона": f"{total_concrete_volume:.1f} м³",
        "Вес арматуры": f"{reinforcement_weight:.0f} кг"
    }

def calculate_formwork(length, width, depth, wall_thickness):
    """
    Расчет опалубки и армирования
    
    Args:
        length (float): Длина бассейна в мм (внутренний размер)
        width (float): Ширина бассейна в мм (внутренний размер)
        depth (float): Глубина бассейна в мм (внутренний размер)
        wall_thickness (float): Толщина стен и дна в мм
        
    Returns:
        dict: Словарь с результатами расчета
    """
    # Конвертируем размеры в метры
    length_m = length / 1000
    width_m = width / 1000
    depth_m = depth / 1000
    wall_thickness_m = wall_thickness / 1000
    
    # Наружные размеры бассейна
    outer_length = length_m + 2 * wall_thickness_m
    outer_width = width_m + 2 * wall_thickness_m
    
    # Наружный периметр
    outer_perimeter = 2 * (outer_length + outer_width)
    
    # Высота наружной опалубки (глубина + толщина дна)
    outer_formwork_height = depth_m + wall_thickness_m
    
    # Площадь наружной опалубки
    outer_formwork_area = outer_perimeter * outer_formwork_height
    
    # Внутренний периметр
    inner_perimeter = 2 * (length_m + width_m)
    
    # Высота внутренней опалубки (равна глубине)
    inner_formwork_height = depth_m
    
    # Площадь внутренней опалубки
    inner_formwork_area = inner_perimeter * inner_formwork_height
    
    # Общая площадь опалубки
    total_formwork_area = outer_formwork_area + inner_formwork_area
    
    # Количество листов фанеры (лист 1.5x1.5 м = 2.25 м²), с запасом 20% на распил
    plywood_sheet_area = 2.25  # м²
    plywood_sheets_count = math.ceil(total_formwork_area / plywood_sheet_area * 1.2)
    
    # Площадь армирования (внутренняя площадь стен + площадь дна)
    reinforcement_area = inner_perimeter * depth_m + length_m * width_m
    
    # Вес арматуры (примерно 5 кг/м² для двойного армирования)
    rebar_weight = reinforcement_area * 5  # кг
    
    # Длина бруса 50x100 (для опалубки, примерно 3 м/п на 1 м² опалубки)
    timber_length = total_formwork_area * 3  # метры
    
    return {
        "Площадь наружной опалубки": f"{outer_formwork_area:.1f} м²",
        "Площадь внутренней опалубки": f"{inner_formwork_area:.1f} м²",
        "Общая площадь опалубки": f"{total_formwork_area:.1f} м²",
        "Количество листов фанеры": f"{plywood_sheets_count}",
        "Вес арматуры": f"{rebar_weight:.0f} кг",
        "Длина бруса 50x100": f"{timber_length:.0f} м"
    }

def calculate_finishing_cost(basic_dims, profile_id="kp1"):
    """
    Расчет стоимости отделочных работ с учетом профиля КП
    
    Args:
        basic_dims (dict): Словарь с основными размерами или сырыми значениями
        profile_id (str): Идентификатор профиля КП
        
    Returns:
        dict: Словарь с расчетами стоимости отделочных работ
    """
    # Получаем параметры профиля
    if isinstance(profile_id, dict):
        # Если передан словарь вместо строки, извлекаем id
        profile_id = profile_id.get("id", "kp1")
    
    # Убеждаемся, что profile_id - строка
    if not isinstance(profile_id, str):
        profile_id = "kp1"
        
    try:
        profile = get_profile(profile_id)
    except Exception as e:
        app.logger.error("Error getting profile in calculate_finishing_cost: %s", str(e))
        profile = get_profile("kp1")  # Используем KP1 по умолчанию
    
    # Определяем, переданы ли сырые значения или словарь с форматированными значениями
    finishing_area = 0
    perimeter = 0
    
    try:
        # Если есть _raw, используем его для извлечения числовых значений
        if isinstance(basic_dims, dict) and "_raw" in basic_dims:
            raw_data = basic_dims["_raw"]
            if isinstance(raw_data, dict):
                finishing_area = raw_data.get("Площадь под отделку", 0)
                # Если не нашли "Площадь под отделку", используем альтернативные ключи
                if finishing_area == 0:
                    finishing_area = raw_data.get("finishing_area", 0)
                
                perimeter = raw_data.get("Периметр", 0)
                # Если не нашли "Периметр", используем альтернативные ключи
                if perimeter == 0:
                    perimeter = raw_data.get("perimeter", 0)
        
        # Если не удалось извлечь из _raw, пробуем извлечь из основных полей
        if finishing_area == 0 and isinstance(basic_dims, dict):
            if "Площадь под отделку" in basic_dims:
                value = basic_dims["Площадь под отделку"]
                if isinstance(value, (int, float)):
                    finishing_area = value
                elif isinstance(value, str):
                    try:
                        # Извлекаем число из строки вида "71.6 м²"
                        parts = value.split()
                        if parts:
                            finishing_area = float(parts[0].replace(',', '.'))
                    except (ValueError, IndexError) as e:
                        app.logger.warning("Error extracting finishing_area from '%s': %s", value, str(e))
            
            # Альтернативное название
            elif "finishing_area" in basic_dims:
                value = basic_dims["finishing_area"]
                if isinstance(value, (int, float)):
                    finishing_area = value
                elif isinstance(value, str):
                    try:
                        parts = value.split()
                        if parts:
                            finishing_area = float(parts[0].replace(',', '.'))
                    except (ValueError, IndexError) as e:
                        app.logger.warning("Error extracting finishing_area from '%s': %s", value, str(e))
            
            # Так же с периметром
            if "Периметр" in basic_dims:
                value = basic_dims["Периметр"]
                if isinstance(value, (int, float)):
                    perimeter = value
                elif isinstance(value, str):
                    try:
                        parts = value.split()
                        if parts:
                            perimeter = float(parts[0].replace(',', '.'))
                    except (ValueError, IndexError) as e:
                        app.logger.warning("Error extracting perimeter from '%s': %s", value, str(e))
            
            # Альтернативное название
            elif "perimeter" in basic_dims:
                value = basic_dims["perimeter"]
                if isinstance(value, (int, float)):
                    perimeter = value
                elif isinstance(value, str):
                    try:
                        parts = value.split()
                        if parts:
                            perimeter = float(parts[0].replace(',', '.'))
                    except (ValueError, IndexError) as e:
                        app.logger.warning("Error extracting perimeter from '%s': %s", value, str(e))
    
    except Exception as e:
        app.logger.error("Error extracting dimensions in calculate_finishing_cost: %s", str(e))
        # В случае ошибки используем значения по умолчанию
        # Значения из KP1
        finishing_area = profile["basic_dimensions"].get("finishing_area", 71.6)
        perimeter = profile["basic_dimensions"].get("perimeter", 24.0)
    
    # Для КП1 используем фиксированные значения из КП
    if profile_id == "kp1":
        try:
            # Лайнер и работы по его установке
            lining_area = profile["kp_params"].get("lining_area", finishing_area)
            lining_price = profile.get("lining_price", 5400)
            lining_cost = lining_area * lining_price
            
            # Копинговый камень
            coping_stone_count = profile["kp_params"].get("coping_stone_count", int(perimeter / 0.5))  # Примерно 1 штука на 0.5 метра
            coping_stone_price = profile["materials_prices"].get("coping_stone", 2600)
            coping_stone_cost = coping_stone_count * coping_stone_price
            
            # Стоимость работы (обычно включена в стоимость лайнера)
            work_cost = 0  # В данном случае работа включена в стоимость лайнера
            
            total_cost = lining_cost + coping_stone_cost
        except Exception as e:
            app.logger.error("Error calculating KP1 finishing cost: %s", str(e))
            lining_cost = finishing_area * 5400  # Примерная стоимость лайнера
            coping_stone_cost = perimeter * 5200  # Примерная стоимость копингового камня
            work_cost = 0
            total_cost = lining_cost + coping_stone_cost

        return {
            "area": finishing_area,
            "perimeter": perimeter,
            "lining": {
                "cost": lining_cost,
                "cost_str": f"{lining_cost:,.0f} руб.".replace(",", " ")
            },
            "coping_stone": {
                "cost": coping_stone_cost,
                "total": coping_stone_cost,
                "cost_str": f"{coping_stone_cost:,.0f} руб.".replace(",", " ")
            },
            "material_cost": lining_cost,
            "material_cost_str": f"{lining_cost:,.0f} руб.".replace(",", " "),
            "work_cost": work_cost,
            "work_cost_str": f"{work_cost:,.0f} руб.".replace(",", " "),
            "total_cost": total_cost,
            "total_cost_str": f"{total_cost:,.0f} руб.".replace(",", " ")
        }
    
    # Для других профилей можно реализовать аналогичный расчет
    elif profile_id == "kp2":
        try:
            # Плитка и работы по её укладке
            materials_prices = profile.get("materials_prices", {})
            tile_price = materials_prices.get("tile", 2500)
            grout_price = materials_prices.get("grout", 300)
            adhesive_price = materials_prices.get("tile_adhesive", 400)
            waterproofing_price = materials_prices.get("waterproofing", 800)
            
            tile_cost = finishing_area * tile_price
            grout_cost = finishing_area * grout_price
            adhesive_cost = finishing_area * adhesive_price
            waterproofing_cost = finishing_area * waterproofing_price
            
            materials_cost = tile_cost + grout_cost + adhesive_cost + waterproofing_cost
            
            # Стоимость работы
            works_prices = profile.get("works_prices", {})
            laying_price = works_prices.get("tile_laying", 2500)
            grouting_price = works_prices.get("grouting", 300)
            
            laying_cost = finishing_area * laying_price
            grouting_cost = finishing_area * grouting_price
            
            work_cost = laying_cost + grouting_cost
            
            total_cost = materials_cost + work_cost
        except Exception as e:
            app.logger.error("Error calculating KP2 finishing cost: %s", str(e))
            materials_cost = finishing_area * 4000  # Примерная стоимость материалов
            work_cost = finishing_area * 2800      # Примерная стоимость работ
            total_cost = materials_cost + work_cost
            tile_cost = finishing_area * 2500
            grout_cost = finishing_area * 300
            adhesive_cost = finishing_area * 400
            waterproofing_cost = finishing_area * 800
            laying_cost = finishing_area * 2500
            grouting_cost = finishing_area * 300
        
        return {
            "area": finishing_area,
            "perimeter": perimeter,
            "materials": {
                "Плитка": f"{tile_cost:,.0f} руб.".replace(",", " "),
                "Затирка": f"{grout_cost:,.0f} руб.".replace(",", " "),
                "Клей для плитки": f"{adhesive_cost:,.0f} руб.".replace(",", " "),
                "Гидроизоляция": f"{waterproofing_cost:,.0f} руб.".replace(",", " ")
            },
            "works": {
                "Укладка плитки": f"{laying_cost:,.0f} руб.".replace(",", " "),
                "Затирка швов": f"{grouting_cost:,.0f} руб.".replace(",", " ")
            },
            "material_cost": materials_cost,
            "material_cost_str": f"{materials_cost:,.0f} руб.".replace(",", " "),
            "work_cost": work_cost,
            "work_cost_str": f"{work_cost:,.0f} руб.".replace(",", " "),
            "total_cost": total_cost,
            "total_cost_str": f"{total_cost:,.0f} руб.".replace(",", " ")
        }
    
    # По умолчанию используем простой расчет для KP3 или других профилей
    else:
        try:
            # Общая стоимость материалов и работ для отделки
            materials_cost = finishing_area * 3000  # Примерная стоимость материалов за м²
            work_cost = finishing_area * 2000       # Примерная стоимость работы за м²
            
            total_cost = materials_cost + work_cost
        except Exception as e:
            app.logger.error("Error calculating default finishing cost: %s", str(e))
            materials_cost = 0
            work_cost = 0
            total_cost = 0
        
        return {
            "area": finishing_area,
            "perimeter": perimeter,
            "material_cost": materials_cost,
            "material_cost_str": f"{materials_cost:,.0f} руб.".replace(",", " "),
            "work_cost": work_cost,
            "work_cost_str": f"{work_cost:,.0f} руб.".replace(",", " "),
            "total_cost": total_cost,
            "total_cost_str": f"{total_cost:,.0f} руб.".replace(",", " ")
        }

def calculate_materials_cost(basic_dims, profile_id):
    """
    Расчет стоимости материалов

    Args:
        basic_dims (dict): Словарь с основными размерами. Может содержать основные размеры или сырые значения.
        profile_id (str): Идентификатор профиля КП

    Returns:
        dict: Словарь со стоимостью материалов и общей стоимостью
    """
    # Получаем профиль КП
    profile = get_profile(profile_id)
    if not profile:
        return {"error": "Профиль не найден", "total_cost": 0}
    
    # Получаем фиксированную стоимость материалов из профиля для KP1
    total_materials_cost = profile["costs"]["materials_total"]
    
    # Создаем форматированные элементы для отображения
    materials = {}
    
    # Для отображения в интерфейсе разбиваем общую стоимость на категории
    # Эти значения примерные и взяты из КП
    if profile_id == "kp1":
        materials = {
            "Земляные работы": f"{48800:,} руб.".replace(",", " "),
            "Транспорт": f"{97500:,} руб.".replace(",", " "),
            "Песок и щебень": f"{17300:,} руб.".replace(",", " "),
            "Материалы опалубки": f"{144500:,} руб.".replace(",", " "),
            "Арматура и сопутствующие": f"{177000:,} руб.".replace(",", " "),
            "Бетон с доставкой": f"{169750:,} руб.".replace(",", " "),
            "Вспомогательные материалы": f"{162026:,} руб.".replace(",", " ")
        }
    elif profile_id == "kp2":
        # Для KP2 можем просто разделить общую сумму на категории
        materials = {
            "Строительные материалы": f"{275000:,} руб.".replace(",", " "),
            "Отделочные материалы": f"{180000:,} руб.".replace(",", " "),
            "Вспомогательные материалы": f"{128398:,} руб.".replace(",", " ")
        }
    elif profile_id == "kp3":
        # Для KP3 можем просто разделить общую сумму на категории
        materials = {
            "Строительные материалы": f"{180000:,} руб.".replace(",", " "),
            "Отделочные материалы": f"{90000:,} руб.".replace(",", " "),
            "Вспомогательные материалы": f"{50631:,} руб.".replace(",", " ")
        }
    
    return {
        "materials": materials,
        "total_cost": total_materials_cost,
        "total_cost_str": f"{total_materials_cost:,} руб.".replace(",", " ")
    }

def calculate_works_cost(basic_dims, profile_id):
    """
    Расчет стоимости работ
    
    Args:
        basic_dims (dict): Словарь с основными размерами
        profile_id (str): Идентификатор профиля КП
        
    Returns:
        dict: Словарь со стоимостью работ и общей стоимостью
    """
    # Получаем профиль КП
    profile = get_profile(profile_id)
    if not profile:
        return {"error": "Профиль не найден", "total_cost": 0}
    
    # Получаем фиксированную стоимость работ из профиля для KP1
    total_works_cost = profile["costs"]["works_total"]
    
    # Создаем форматированные элементы для отображения
    works = {}
    
    # Для отображения в интерфейсе разбиваем общую стоимость на категории
    # Эти значения примерные и взяты из КП
    if profile_id == "kp1":
        works = {
            "Подготовительные работы": f"{73000:,} руб.".replace(",", " "),
            "Земляные работы": f"{29000:,} руб.".replace(",", " "),
            "Бетонирование": f"{177600:,} руб.".replace(",", " "),
            "Опалубка и армирование": f"{204260:,} руб.".replace(",", " "),
            "Монтаж закладных": f"{40500:,} руб.".replace(",", " "),
            "Обратная засыпка": f"{50400:,} руб.".replace(",", " "),
            "Отделочные работы": f"{252100:,} руб.".replace(",", " "),
            "Монтаж бортового камня": f"{65000:,} руб.".replace(",", " "),
            "Разгрузка материалов": f"{30000:,} руб.".replace(",", " ")
        }
    elif profile_id == "kp2":
        # Для KP2 можем просто разделить общую сумму на категории
        works = {
            "Подготовительные и земляные работы": f"{120000:,} руб.".replace(",", " "),
            "Бетонные работы": f"{180000:,} руб.".replace(",", " "),
            "Опалубка и армирование": f"{105000:,} руб.".replace(",", " "),
            "Отделочные работы": f"{170690:,} руб.".replace(",", " "),
            "Монтаж бортового камня": f"{40000:,} руб.".replace(",", " ")
        }
    elif profile_id == "kp3":
        # Для KP3 можем просто разделить общую сумму на категории
        works = {
            "Подготовительные и земляные работы": f"{90000:,} руб.".replace(",", " "),
            "Бетонные работы": f"{104284:,} руб.".replace(",", " "),
            "Опалубка и армирование": f"{90000:,} руб.".replace(",", " "),
            "Отделочные работы": f"{110000:,} руб.".replace(",", " ")
        }
    
    return {
        "works": works,
        "total_cost": total_works_cost,
        "total_cost_str": f"{total_works_cost:,} руб.".replace(",", " ")
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

def calculate_kp_items(length, width, depth, pool_type, profile_id="kp1"):
    """Расчет позиций для коммерческого предложения в формате ООО "ДОН БАСС" 
    
    Args:
        length (float): Длина бассейна в мм
        width (float): Ширина бассейна в мм
        depth (float): Глубина бассейна в мм
        pool_type (str): Тип бассейна (liner, tile, mosaic)
        profile_id (str): Идентификатор профиля КП
        
    Returns:
        dict: Словарь с позициями КП и итоговыми суммами
    """
    # Получаем профиль КП
    try:
        profile = get_profile(profile_id)
        if not profile:
            logging.warning(f"Профиль {profile_id} не найден, используется KP1")
            profile = get_profile("kp1")
            profile_id = "kp1"
    except Exception as e:
        logging.error(f"Ошибка при получении профиля: {e}")
        profile = get_profile("kp1")
        profile_id = "kp1"
    
    # Получаем эталонные значения стоимости из профиля
    reference_materials = profile["costs"]["materials_total"]
    reference_works = profile["costs"]["works_total"]
    reference_equipment = profile["costs"]["equipment_total"]
    
    # Преобразуем размеры в метры
    length_m = length / 1000
    width_m = width / 1000
    depth_m = depth / 1000
    
    # Рассчитываем основные размеры бассейна
    water_surface = length_m * width_m
    perimeter = 2 * (length_m + width_m)
    wall_area = perimeter * depth_m
    finishing_area = water_surface + wall_area
    water_volume = water_surface * depth_m
    
    # Эталонные размеры из КП №1 (8000x4000x1500)
    reference_surface = 32.0  # м²
    reference_perimeter = 26.0  # м/п
    reference_volume = 48.0  # м³
    reference_area = 71.6  # м²
    
    # Коэффициенты масштабирования относительно эталонных размеров
    surface_ratio = water_surface / reference_surface
    perimeter_ratio = perimeter / reference_perimeter
    volume_ratio = water_volume / reference_volume
    area_ratio = finishing_area / reference_area
    
    # Рассчитываем коэффициенты масштабирования для основных категорий затрат
    # Материалы - зависят от объема и площади
    materials_scale = (0.4 * surface_ratio) + (0.4 * volume_ratio) + (0.2 * perimeter_ratio)
    # Работы - зависят больше от площади
    works_scale = (0.5 * area_ratio) + (0.3 * volume_ratio) + (0.2 * perimeter_ratio)
    # Оборудование - больше фиксированных компонентов
    equipment_scale = (0.2 * volume_ratio) + (0.1 * perimeter_ratio) + 0.7
    
    # Используем те же наименования, что в КП ООО "ДОН БАСС"
    # Оборудование - количество почти не зависит от размеров
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
            "qty": max(1, round(perimeter_ratio)),  # Количество скиммеров зависит от периметра
            "price": 9115.00
        },
        {
            "name": "Форсунка стеновая под лайнер Aquaviva EM4414 (50 мм/2\" сопло \"круг\", латунные вставки",
            "unit": "шт.",
            "qty": max(2, round(perimeter_ratio * 2)),  # Количество форсунок зависит от периметра
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
            "name": "Инсталляция (трубы, краны, фитинги)",
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
            "name": "Теплообменник Elecro G2 HE 49 кВт (титан)",
            "unit": "шт.",
            "qty": 1,
            "price": 84800.00
        },
        {
            "name": "Теплообменник Elecro 18 кВт Space Heater (пластик)",
            "unit": "шт.",
            "qty": 1,
            "price": 33200.00
        },
        {
            "name": "Установка обеззараживания Sonda Salt 20",
            "unit": "шт.",
            "qty": 1,
            "price": 139000.00
        },
        {
            "name": "Автоматическая станция контроля и дозирования Bayrol Pool Manager PRO",
            "unit": "шт.",
            "qty": 1,
            "price": 186000.00
        },
        {
            "name": "Монтаж и наладка оборудования, запуск",
            "unit": "услуга",
            "qty": 1,
            "price": 186000.00
        }
    ]
    
    # Рассчитываем общую стоимость оборудования
    calculated_equipment_total = sum(item["qty"] * item["price"] for item in equipment_items)
    
    # Приводим к эталонной стоимости из КП с учетом коэффициента масштабирования
    equipment_total = round(reference_equipment * equipment_scale)
    
    # Масштабируем стоимость материалов и работ от эталонных значений
    materials_total = round(reference_materials * materials_scale)
    works_total = round(reference_works * works_scale)
    
    # Материалы - зависят от объема, площади и периметра
    # Показываем основные позиции материалов, но итоговая сумма берется из расчета выше
    materials_items = [
        {
            "name": "Выемка грунта под бассейн механизированным способом",
            "unit": "м3",
            "qty": round(122 * volume_ratio),  # Зависит от объема
            "price": 400.00
        },
        {
            "name": "Вывоз чистого грунта с территории участка",
            "unit": "КамАЗ",
            "qty": max(1, round(15 * volume_ratio)),  # Зависит от объема
            "price": 6500.00
        },
        {
            "name": "Песок по факту с доставкой 6 м3",
            "unit": "шт.",
            "qty": max(1, round(volume_ratio)),
            "price": 7600.00
        },
        {
            "name": "Щебень по факту с доставкой 10 т",
            "unit": "шт.",
            "qty": max(1, round(volume_ratio)),
            "price": 9700.00
        },
        {
            "name": "Бетон М200 для подбетонки с доставкой",
            "unit": "м3",
            "qty": round(3.6 * surface_ratio, 1),  # Зависит от площади
            "price": 5750.00
        },
        {
            "name": "Бетон М300 для чаши бассейна с доставкой",
            "unit": "м3",
            "qty": round(14.6 * volume_ratio, 1),  # Зависит от объема
            "price": 6650.00
        },
        {
            "name": "Арматура диаметром 10 мм",
            "unit": "т",
            "qty": round(1.8 * area_ratio, 1),  # Зависит от площади отделки
            "price": 65000.00
        }
    ]
    
    # Работы - зависят от площади, объема и периметра
    works_items = [
        {
            "name": "Разметка бассейна для техники, нивелировка, привязка к территории по всем этапам работ",
            "unit": "м2",
            "qty": round(water_surface * 1.7),  # Зависит от площади
            "price": 600.00
        },
        {
            "name": "Вязка арматуры для чаши бассейна",
            "unit": "м2",
            "qty": round(finishing_area),  # Зависит от общей площади
            "price": 1750.00
        },
        {
            "name": "Устройство опалубки с применением гидрофобной фанеры",
            "unit": "м2",
            "qty": round(wall_area * 2.2),  # Зависит от площади стен (внутренняя + внешняя)
            "price": 550.00
        },
        {
            "name": "Приемка и заливка бетоном М200 подбетонки",
            "unit": "м3",
            "qty": round(3.6 * surface_ratio, 1),  # Зависит от площади
            "price": 1200.00
        },
        {
            "name": "Приемка и заливка бетоном М300 чаши",
            "unit": "м3",
            "qty": round(14.6 * volume_ratio, 1),  # Зависит от объема
            "price": 3500.00
        },
        {
            "name": "Разгрузка и подноска строительных материалов",
            "unit": "услуга",
            "qty": 1,
            "price": 30000.00
        }
    ]
    
    # Рассчитываем общую стоимость
    total_cost = equipment_total + materials_total + works_total
    
    return {
        "equipment_items": equipment_items,
        "equipment_total": equipment_total,
        "materials_items": materials_items,
        "materials_total": materials_total,
        "works_items": works_items,
        "works_total": works_total,
        "total_cost": total_cost
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
    Расчет параметров бассейна по заданным размерам
    
    Ожидает данные в формате JSON:
    {
        "length": float, // длина бассейна в мм
        "width": float, // ширина бассейна в мм
        "depth": float, // глубина бассейна в мм
        "wall_thickness": float, // толщина стенки в мм
        "profile_id": string // необязательный, идентификатор профиля КП
    }
    """
    try:
        data = request.get_json()
        app.logger.debug('Received data: %s', data)
        
        if not data:
            return jsonify({"error": "Отсутствуют данные JSON"}), 400
        
        # Проверяем наличие всех необходимых параметров
        required_params = ["length", "width", "depth", "wall_thickness"]
        for param in required_params:
            if param not in data:
                return jsonify({"error": f"Отсутствует параметр {param}"}), 400
        
        length = float(data["length"])
        width = float(data["width"])
        depth = float(data["depth"])
        wall_thickness = float(data["wall_thickness"])
        
        # Обрабатываем разные варианты имени параметра для профиля
        profile_id = data.get("profile_id", None)
        if profile_id is None:
            profile_id = data.get("profile", "kp1")  # Альтернативное имя параметра
        else:
            profile_id = profile_id  # Если указан profile_id, используем его
        
        # Для обратной совместимости - если передан pool_type, но не profile_id и не profile
        if "pool_type" in data and not profile_id:
            if data["pool_type"] == "liner":
                profile_id = "kp1"
            elif data["pool_type"] == "tile":
                profile_id = "kp2"
            elif data["pool_type"] == "mosaic":
                profile_id = "kp3"
        
        # Если после всех проверок profile_id не задан, используем значение по умолчанию
        if not profile_id:
            profile_id = "kp1"
        
        app.logger.debug('Using profile_id: %s', profile_id)
        
        # Вызываем функцию расчета
        result = calculate(length, width, depth, wall_thickness, profile_id)
        
        if "error" in result:
            return jsonify({"error": result["error"]}), 400
        
        return jsonify(result)
    
    except ValueError as e:
        return jsonify({"error": f"Ошибка преобразования типов: {str(e)}"}), 400
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/compare_estimate', methods=['POST'])
def compare_estimate():
    """
    Сравнивает расчетные значения со значениями, указанными в КП
    
    Ожидает данные в формате JSON:
    {
        "length": float, // длина бассейна в метрах
        "width": float, // ширина бассейна в метрах
        "depth": float, // глубина бассейна в метрах
        "wall_thickness": float, // толщина стенки в см
        "profile_id": string, // идентификатор профиля КП (kp1, kp2, kp3)
        "pool_type": string, // тип бассейна (liner, tile, mosaic)
        "estimate": {
            "water_surface": float, // площадь водной поверхности из КП
            "perimeter": float, // периметр из КП
            "wall_area": float, // площадь стен из КП
            "finishing_area": float, // площадь отделки из КП
            "water_volume": float, // объем воды из КП
            "materials_cost": float, // стоимость материалов из КП
            "work_cost": float, // стоимость работ из КП
            "equipment_cost": float, // стоимость оборудования из КП
            "total_cost": float // общая стоимость из КП
        }
    }
    """
    try:
        data = request.get_json()
        app.logger.debug('Received data for compare_estimate: %s', data)
        
        if not data:
            return jsonify({"success": False, "error": "Не получены данные"}), 400
        
        # Извлекаем параметры запроса с проверкой
        try:
            length = float(data.get("length", 0))
            width = float(data.get("width", 0))
            depth = float(data.get("depth", 0))
            wall_thickness = float(data.get("wall_thickness", 0))
        except (ValueError, TypeError) as e:
            app.logger.error('Invalid dimensions data: %s', str(e))
            return jsonify({"success": False, "error": f"Неверный формат размеров: {str(e)}"}), 400
        
        # Получаем profile_id и pool_type
        profile_id = data.get("profile_id", "kp1")
        pool_type = data.get("pool_type", "liner")
        
        # Если profile_id не указан явно, определяем его по pool_type
        if not profile_id or profile_id == "":
            if pool_type == "liner":
                profile_id = "kp1"
            elif pool_type == "tile":
                profile_id = "kp2"
            elif pool_type == "mosaic":
                profile_id = "kp3"
            else:
                profile_id = "kp1"  # Значение по умолчанию
        
        # Извлекаем данные из КП
        estimate_data = data.get("estimate", {})
        if not estimate_data:
            app.logger.warning('No estimate data provided')
        
        # Выполняем расчет с нашими алгоритмами
        try:
            calc_result = calculate(length, width, depth, wall_thickness, profile_id)
        except Exception as calc_error:
            app.logger.error('Error during calculation: %s', str(calc_error), exc_info=True)
            return jsonify({"success": False, "error": f"Ошибка при расчете: {str(calc_error)}"}), 500
        
        # Вспомогательная функция для безопасного извлечения числа из строки
        def safe_extract_float(string_value):
            if string_value is None:
                return 0
            try:
                if isinstance(string_value, (int, float)):
                    return float(string_value)
                return float(string_value.replace(',', '.').replace(' ', ''))
            except (ValueError, AttributeError):
                return 0
        
        # Вспомогательная функция для безопасного извлечения числа из строки с единицами измерения
        def safe_extract_measurement(string_value):
            if string_value is None:
                return 0
            try:
                if isinstance(string_value, (int, float)):
                    return float(string_value)
                    
                # Извлекаем число из строки вида "32.0 м²"
                parts = string_value.split()
                if parts and parts[0]:
                    return float(parts[0].replace(',', '.'))
                return 0
            except (ValueError, AttributeError, IndexError):
                app.logger.warning('Failed to extract measurement from: %s', string_value)
                return 0
                
        # Сравниваем размеры
        dimensions_comparison = {}
        
        # Извлекаем значения из calc_result и estimate_data с обработкой ошибок
        try:
            calc_water_surface = safe_extract_measurement(calc_result["basic_dimensions"].get("Площадь водного зеркала", "0"))
            calc_perimeter = safe_extract_measurement(calc_result["basic_dimensions"].get("Периметр", "0"))
            calc_wall_area = safe_extract_measurement(calc_result["basic_dimensions"].get("Площадь стен", "0"))
            calc_finishing_area = safe_extract_measurement(calc_result["basic_dimensions"].get("Площадь отделки", "0"))
            calc_water_volume = safe_extract_measurement(calc_result["basic_dimensions"].get("Объем воды", "0"))
        except Exception as e:
            app.logger.error('Error extracting calculated dimensions: %s', str(e), exc_info=True)
            return jsonify({"success": False, "error": f"Ошибка при извлечении размеров: {str(e)}"}), 500
        
        # Извлекаем значения из estimate_data
        try:
            estimate_water_surface = safe_extract_float(estimate_data.get("water_surface", 0))
            estimate_perimeter = safe_extract_float(estimate_data.get("perimeter", 0))
            estimate_wall_area = safe_extract_float(estimate_data.get("wall_area", 0))
            estimate_finishing_area = safe_extract_float(estimate_data.get("finishing_area", 0))
            estimate_water_volume = safe_extract_float(estimate_data.get("water_volume", 0))
        except Exception as e:
            app.logger.error('Error extracting estimate dimensions: %s', str(e), exc_info=True)
            return jsonify({"success": False, "error": f"Ошибка при извлечении размеров из КП: {str(e)}"}), 500
            
        # Формируем сравнение размеров
        dimensions_comparison = {
            "water_surface": {
                "calc": calc_water_surface,
                "estimate": estimate_water_surface,
                "diff": round(calc_water_surface - estimate_water_surface, 2)
            },
            "perimeter": {
                "calc": calc_perimeter,
                "estimate": estimate_perimeter,
                "diff": round(calc_perimeter - estimate_perimeter, 2)
            },
            "wall_area": {
                "calc": calc_wall_area,
                "estimate": estimate_wall_area,
                "diff": round(calc_wall_area - estimate_wall_area, 2)
            },
            "finishing_area": {
                "calc": calc_finishing_area,
                "estimate": estimate_finishing_area,
                "diff": round(calc_finishing_area - estimate_finishing_area, 2)
            },
            "water_volume": {
                "calc": calc_water_volume,
                "estimate": estimate_water_volume,
                "diff": round(calc_water_volume - estimate_water_volume, 2)
            }
        }
        
        # Сравниваем стоимость
        try:
            calc_materials = calc_result["costs"]["materials_total"]
            calc_works = calc_result["costs"]["works_total"]
            calc_equipment = calc_result["costs"]["equipment_total"]
            calc_total = calc_result["costs"]["total"]
        except KeyError as e:
            app.logger.error('Missing cost key in calculation result: %s', str(e), exc_info=True)
            return jsonify({"success": False, "error": f"Ошибка при извлечении стоимости: {str(e)}"}), 500
            
        try:
            estimate_materials = safe_extract_float(estimate_data.get("materials_cost", 0))
            estimate_works = safe_extract_float(estimate_data.get("work_cost", 0))
            estimate_equipment = safe_extract_float(estimate_data.get("equipment_cost", 0))
            estimate_total = safe_extract_float(estimate_data.get("total_cost", 0))
        except Exception as e:
            app.logger.error('Error extracting estimate costs: %s', str(e), exc_info=True)
            return jsonify({"success": False, "error": f"Ошибка при извлечении стоимости из КП: {str(e)}"}), 500
        
        costs_comparison = {
            "materials": {
                "calc": calc_materials,
                "estimate": estimate_materials,
                "diff": round(calc_materials - estimate_materials)
            },
            "work": {
                "calc": calc_works,
                "estimate": estimate_works,
                "diff": round(calc_works - estimate_works)
            },
            "equipment": {
                "calc": calc_equipment,
                "estimate": estimate_equipment,
                "diff": round(calc_equipment - estimate_equipment)
            },
            "total": {
                "calc": calc_total,
                "estimate": estimate_total,
                "diff": round(calc_total - estimate_total)
            }
        }
        
        app.logger.debug('Comparison results: %s', {
            "dimensions": dimensions_comparison,
            "costs": costs_comparison
        })
        
        return jsonify({
            "success": True,
            "comparison": {
                "dimensions": dimensions_comparison,
                "costs": costs_comparison
            }
        })
        
    except Exception as e:
        app.logger.error('Error in compare_estimate: %s', str(e), exc_info=True)
        return jsonify({"success": False, "error": str(e)})

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
    Главная функция расчета, вызывает все остальные функции и формирует итоговый результат
    
    Args:
        length (float): длина бассейна в мм
        width (float): ширина бассейна в мм
        depth (float): глубина бассейна в мм
        wall_thickness (float): толщина стенки в мм
        profile_id (str): идентификатор профиля КП
        
    Returns:
        dict: Результаты расчета или ошибка
    """
    try:
        app.logger.debug("Profile_id: %s", profile_id)
        
        # Проверка входных данных
        if not all(isinstance(x, (int, float)) and x > 0 for x in [length, width, depth, wall_thickness]):
            return {"error": "Все размеры должны быть положительными числами"}
        
        # Обеспечение совместимости типов для profile_id
        if isinstance(profile_id, dict):
            app.logger.debug("Converting profile_id from dict: %s", profile_id)
            profile_id = profile_id.get("id", "kp1")
        
        if not profile_id or not isinstance(profile_id, str):
            app.logger.debug("Using default profile_id 'kp1' instead of %s", profile_id)
            profile_id = "kp1"
        
        # Получаем параметры профиля
        try:
            profile = get_profile(profile_id)
            app.logger.debug("Using profile: %s", profile["name"])
        except Exception as e:
            app.logger.error("Error getting profile %s: %s", profile_id, str(e))
            return {"error": f"Ошибка при получении профиля {profile_id}: {str(e)}"}
        
        # Создаем размеры для вычисления коэффициентов коррекции
        dimensions = {
            "length": length,
            "width": width,
            "depth": depth,
            "wall_thickness": wall_thickness
        }
        
        # Получаем коэффициенты корректировки размеров
        try:
            correction_factors = get_dimensions_correction_factor(profile_id, dimensions)
        except Exception as e:
            app.logger.error("Error calculating correction factors: %s", str(e))
            correction_factors = None  # Используем значение по умолчанию
        
        # Рассчитываем базовые размеры
        try:
            basic_dims = calculate_basic_dimensions(length, width, depth, wall_thickness, correction_factors)
        except Exception as e:
            app.logger.error("Error calculating basic dimensions: %s", str(e))
            return {"error": f"Ошибка при расчете базовых размеров: {str(e)}"}
        
        # Получаем сырые числовые значения для дальнейших расчетов
        raw_dims = {}
        
        for key, value in basic_dims.items():
            if key == "_raw":
                continue
                
            if isinstance(value, str):
                # Пытаемся извлечь числовое значение из строки вида "32.0 м²"
                parts = value.split()
                if parts and parts[0]:
                    try:
                        raw_value = float(parts[0].replace(',', '.'))
                        raw_dims[key] = raw_value
                    except (ValueError, TypeError):
                        app.logger.warning("Could not extract number from %s", value)
            elif isinstance(value, (int, float)):
                raw_dims[key] = value
        
        # Сохраняем сырые значения в основной словарь
        basic_dims["_raw"] = raw_dims
        
        # Рассчитываем земляные работы
        try:
            earthworks = calculate_earthworks(length, width, depth, wall_thickness)
        except Exception as e:
            app.logger.error("Error calculating earthworks: %s", str(e))
            return {"error": f"Ошибка при расчете земляных работ: {str(e)}"}
        
        # Рассчитываем бетонные работы
        try:
            concrete_works = calculate_concrete_works(length, width, depth, wall_thickness)
        except Exception as e:
            app.logger.error("Error calculating concrete works: %s", str(e))
            return {"error": f"Ошибка при расчете бетонных работ: {str(e)}"}
        
        # Рассчитываем опалубку
        try:
            formwork = calculate_formwork(length, width, depth, wall_thickness)
        except Exception as e:
            app.logger.error("Error calculating formwork: %s", str(e))
            return {"error": f"Ошибка при расчете опалубки: {str(e)}"}
        
        # Рассчитываем отделочные работы
        try:
            finishing_cost = calculate_finishing_cost(basic_dims, profile_id)
        except Exception as e:
            app.logger.error("Error calculating finishing cost: %s", str(e))
            finishing_cost = {}  # Пустой словарь в случае ошибки
        
        # Рассчитываем стоимость материалов
        try:
            materials_cost = calculate_materials_cost(basic_dims, profile_id)
        except Exception as e:
            app.logger.error("Error calculating materials cost: %s", str(e))
            materials_cost = {}  # Пустой словарь в случае ошибки
        
        # Рассчитываем стоимость работ
        try:
            works_cost = calculate_works_cost(basic_dims, profile_id)
        except Exception as e:
            app.logger.error("Error calculating works cost: %s", str(e))
            works_cost = {}  # Пустой словарь в случае ошибки
        
        # Рассчитываем элементы КП
        try:
            # Определяем тип бассейна по профилю
            pool_type = "liner"  # По умолчанию
            if profile_id == "kp2":
                pool_type = "tile"
            elif profile_id == "kp3":
                pool_type = "mosaic"
                
            kp_items = calculate_kp_items(length, width, depth, pool_type, profile_id)
        except Exception as e:
            app.logger.error("Error calculating KP items: %s", str(e))
            # В случае ошибки создаем структуру с нулевыми значениями
            kp_items = {
                "equipment_items": [],
                "materials_items": [],
                "works_items": [],
                "equipment_total": 0,
                "materials_total": 0,
                "works_total": 0,
                "total_cost": 0
            }
        
        # Формируем общую стоимость для бассейна
        try:
            # Получаем значения из kp_items
            materials_total = kp_items.get("materials_total", 0)
            works_total = kp_items.get("works_total", 0)
            equipment_total = kp_items.get("equipment_total", 0)
            
            # Вычисляем общую сумму как сумму всех компонентов
            total_cost = materials_total + works_total + equipment_total
            
            costs = {
                "materials_total": materials_total,
                "works_total": works_total,
                "equipment_total": equipment_total,
                "total": total_cost
            }
        except Exception as e:
            app.logger.error("Error calculating costs: %s", str(e))
            costs = {
                "materials_total": 0,
                "works_total": 0,
                "equipment_total": 0,
                "total": 0
            }
        
        # Формируем данные о бассейне для возврата
        try:
            pool_data = {
                "profile": {
                    "id": profile_id,
                    "name": profile.get("name", f"Профиль {profile_id}")
                },
                "dimensions": {
                    "length": length,
                    "width": width,
                    "depth": depth,
                    "wall_thickness": wall_thickness
                }
            }
        except Exception as e:
            app.logger.error("Error building pool data: %s", str(e))
            pool_data = {
                "profile": {
                    "id": profile_id,
                    "name": f"Профиль {profile_id}"
                },
                "dimensions": {
                    "length": length,
                    "width": width,
                    "depth": depth,
                    "wall_thickness": wall_thickness
                }
            }
        
        # Формируем итоговый результат
        result = {
            "basic_dimensions": basic_dims,
            "earthworks": earthworks,
            "concrete_works": concrete_works,
            "formwork": formwork,
            "finishing_cost": finishing_cost,
            "materials_cost": materials_cost,
            "works_cost": works_cost,
            "kp_items": kp_items,
            "costs": costs,
            "pool_data": pool_data
        }
        
        return result
        
    except Exception as e:
        app.logger.error("Unexpected error in calculate: %s", str(e), exc_info=True)
        return {"error": f"Неожиданная ошибка при расчете: {str(e)}"}

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 3000))
    app.run(host='0.0.0.0', port=port, debug=True) 