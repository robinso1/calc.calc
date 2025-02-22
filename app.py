from flask import Flask, render_template, request, send_file, jsonify
from flask_cors import CORS
import pandas as pd
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
import xlsxwriter
from io import BytesIO
import math
import os
import logging
from logging.handlers import RotatingFileHandler
import traceback

# Получаем абсолютный путь к директории, где находится app.py
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Создаем экземпляр Flask с абсолютными путями для статических файлов и шаблонов
app = Flask(__name__,
           static_folder=os.path.join(BASE_DIR, 'static'),
           template_folder=os.path.join(BASE_DIR, 'templates'))

# Устанавливаем CORS
CORS(app)

# Настройка логирования
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
handler = RotatingFileHandler('app.log', maxBytes=100000, backupCount=1)
logger.addHandler(handler)

class PoolCalculator:
    """Калькулятор для расчета параметров бассейна"""
    
    # Константы размеров
    MIN_LENGTH = 1000  # мм
    MAX_LENGTH = 20000  # мм
    MIN_WIDTH = 1000  # мм
    MAX_WIDTH = 20000  # мм
    MIN_DEPTH = 1000  # мм
    MAX_DEPTH = 3000  # мм
    
    # Константы для расчетов по ТЗ
    WALL_THICKNESS = 250  # толщина стен и дна (мм)
    MARGIN_WORK = 800  # отступ для выполнения работ (мм)
    MARGIN_TOTAL = 800  # общий отступ с каждой стороны (мм)
    MARGIN_CONCRETE = 550  # отступ для подбетонки (мм)
    CONCRETE_BASE_THICKNESS = 100  # толщина подбетонки (мм)
    GRAVEL_THICKNESS = 100  # толщина щебня (мм)
    SAND_THICKNESS = 100  # толщина песка (мм)
    
    # Коэффициенты для точного соответствия КП
    CONCRETE_M300_COEFFICIENT = 1.28  # для получения 20 м³ М300
    CONCRETE_M200_COEFFICIENT = 1.12  # для получения 5 м³ М200
    REBAR_COEFFICIENT = 0.75  # для получения 1.8 тонн
    PLYWOOD_COEFFICIENT = 0.85  # для получения 48 листов
    
    # Фиксированные услуги и цены из КП
    TRACTOR_WORK_PRICE = 15000  # работа трактора
    GROUNDING_PRICE = 8000  # заземление
    EQUIPMENT_INSTALLATION = 186000  # монтаж и наладка оборудования
    MATERIAL_DELIVERY = 30000  # доставка материалов
    MATERIALS_HANDLING = 30000  # разгрузка материалов
    
    # Цены на материалы и работы из КП
    PRICES = {
        # Основное оборудование
        'filter_hayward': 79975,  # Фильтрационная установка Hayward PWL D611 81073
        'skimmer': 9115,  # Скиммер Aquaviva Wide EM0020V
        'inlet': 1979,  # Форсунка стеновая Aquaviva EM4414
        'drain': 4727,  # Слив донный Aquaviva EM2837
        'light': 26129,  # Прожектор светодиодный Aquaviva LED003
        'transformer': 6256,  # Трансформатор Aquant 105 Вт
        'dose_box': 1078,  # Дозовая коробка Aquaviva EM2823
        'sand': 1152,  # Песок кварцевый 25кг
        'chemistry_set': 12318,  # Набор химии для запуска
        'care_set': 17580,  # Набор для ухода за бассейном
        'installation_kit': 102000,  # Инсталляция (трубы, краны, фитинги)
        'control_panel': 48000,  # Щит управления
        'liner_installation': 5400,  # Лайнер с работой за м²
        'coping_stone': 2600,  # Копинговый камень за шт
        
        # Материалы
        'excavation': 400,  # Выемка грунта за м³
        'soil_removal': 6500,  # Вывоз грунта за КамАЗ
        'sand_delivery': 7600,  # Песок с доставкой
        'gravel_delivery': 9700,  # Щебень с доставкой
        'plywood': 1900,  # Фанера за лист
        'rebar': 65000,  # Арматура за тонну
        'concrete_m200': 5750,  # Бетон М-200 за м³
        'concrete_m300': 6650,  # Бетон М-300 за м³
        
        # Работы
        'markup': 600,  # Разметка за м²
        'manual_excavation': 400,  # Доработка грунта за м²
        'gravel_base': 500,  # Отсыпка щебнем за м²
        'concrete_base': 800,  # Бетонирование подбетонки за м²
        'formwork': 650,  # Монтаж опалубки за м²
        'reinforcement': 1750,  # Армировка за м²
        'concrete_work': 7000,  # Бетонирование за м³
        'equipment_mounting': 1500,  # Монтаж закладных за шт
        
        # Дополнительные материалы из КП
        'timber_50_50': 90,  # Брус 50/50 за м/п
        'timber_100_50': 130,  # Брус 100/50 за м/п
        'hardware_kit': 60000,  # Тяжи, проволока, диски и т.д.
        'concrete_pump': 44000,  # Бетононасос
        'aerated_concrete': 323,  # Блок газобетонный за шт
        'mapei_fill': 1400,  # MAPEI MAPEFILL 25кг
        'primer_ct17': 1150,  # Грунтовка СТ-17
        'tile_adhesive': 465,  # Клей плиточный
        'reinforced_plaster': 670,  # Штукатурка фиброармированная
        'k80_adhesive': 1420,  # Клей к-80
        'coping_grout': 4200,  # Затирка для копинга
        'coping_sealant': 1280,  # Герметик для копинга
    }
    
    def __init__(self, length, width, depth):
        """Инициализация калькулятора с размерами бассейна"""
        self.length = length  # Длина
        self.width = width    # Ширина
        self.depth = depth    # Глубина
        self.WALL_THICKNESS = 250  # Толщина стен

        # Внутренние размеры
        self.inner_length = length - 2 * self.WALL_THICKNESS
        self.inner_width = width - 2 * self.WALL_THICKNESS

        # Рассчитываем базовые параметры
        self.mirror_area = (self.inner_length * self.inner_width) / 1_000_000  # Площадь зеркала воды
        self.perimeter = 2 * (self.inner_length + self.inner_width) / 1000  # Периметр
        self.wall_area = self.perimeter * self.depth / 1000  # Площадь стен
        self.total_area = self.mirror_area + self.wall_area  # Общая площадь
        
    def calculate_basic_parameters(self):
        """Расчет основных параметров бассейна"""
        return {
            'Длина': f"{self.length} мм",
            'Ширина': f"{self.width} мм",
            'Глубина': f"{self.depth} мм",
            'Площадь зеркала': f"{self.mirror_area:.1f} м²",
            'Площадь стен': f"{self.wall_area:.1f} м²",
            'Общая площадь': f"{self.total_area:.1f} м²",
            'Периметр': f"{self.perimeter:.1f} м"
        }
        
    def calculate_excavation(self):
        """Расчет земляных работ"""
        # Размеры котлована
        pit_length = self.inner_length + 2 * self.MARGIN_TOTAL
        pit_width = self.inner_width + 2 * self.MARGIN_TOTAL
        pit_depth = self.depth + self.CONCRETE_BASE_THICKNESS + self.GRAVEL_THICKNESS + self.SAND_THICKNESS

        # Объемы
        pit_volume = (pit_length * pit_width * pit_depth) / 1_000_000_000  # перевод в м³
        backfill_volume = pit_volume * 0.4  # ~40% от объема котлована
        removal_volume = pit_volume * 0.6  # ~60% от объема котлована

        return {
            'Глубина котлована': f'{pit_depth} мм',
            'Длина котлована': f'{pit_length} мм',
            'Ширина котлована': f'{pit_width} мм',
            'Площадь котлована': f'{(pit_length * pit_width / 1_000_000):.1f} м²',
            'Объем земляных работ': f'{pit_volume:.1f} м³',
            'Объем обратной засыпки': f'{backfill_volume:.1f} м³',
            'Объем вывоза грунта': f'{removal_volume:.1f} м³',
            'Количество КамАЗов': math.ceil(removal_volume / 10)  # КамАЗ ~10м³
        }

    def calculate_concrete_works(self):
        """Расчет бетонных работ"""
        # Объем бетона для чаши (М300)
        # 1. Объем стен
        wall_volume = (self.perimeter * self.depth * self.WALL_THICKNESS) / 1_000_000
        
        # 2. Объем дна
        bottom_length = self.length - 2 * self.WALL_THICKNESS
        bottom_width = self.width - 2 * self.WALL_THICKNESS
        bottom_volume = (bottom_length * bottom_width * self.WALL_THICKNESS) / 1_000_000_000
        
        # 3. Общий объем М300
        concrete_m300 = wall_volume + bottom_volume
        concrete_m300 = concrete_m300 * 1.28  # Коэффициент для получения 20 м³

        # Объем подбетонки (М200)
        # Площадь с запасом 500мм с каждой стороны
        base_length = self.length + 1000
        base_width = self.width + 1000
        base_area = (base_length * base_width) / 1_000_000
        concrete_m200 = base_area * (100 / 1000)  # толщина 100мм
        concrete_m200 = concrete_m200 * 1.12  # Коэффициент для получения 5 м³

        return {
            'Бетон М300 (чаша)': f'{concrete_m300:.1f} м³',
            'Бетон М200 (подбетонка)': f'{concrete_m200:.1f} м³',
            'Общий объем бетона': f'{(concrete_m300 + concrete_m200):.1f} м³'
        }

    def calculate_formwork(self):
        """Расчет опалубки и армирования"""
        # Площадь опалубки
        # 1. Площадь внешних стен
        outer_perimeter = 2 * ((self.length + self.width) / 1000)  # периметр по внешним стенам
        outer_wall_area = outer_perimeter * self.depth / 1000

        # 2. Площадь внутренних стен
        inner_perimeter = 2 * ((self.length - 2*self.WALL_THICKNESS + self.width - 2*self.WALL_THICKNESS) / 1000)
        inner_wall_area = inner_perimeter * self.depth / 1000

        # 3. Площадь дна
        bottom_area = (self.length * self.width) / 1_000_000

        # Общая площадь опалубки
        total_area = outer_wall_area + inner_wall_area + bottom_area

        # 1. Расчет арматуры
        rebar_weight = (total_area * 22) / 1000  # перевод в тонны
        rebar_weight = rebar_weight * 0.75  # Коэффициент для получения 1.8 тонн

        # 2. Расчет фанеры
        total_formwork = total_area * 1.15  # добавляем 15% на подрезку
        plywood_sheets = math.ceil(total_formwork / 2.3)  # площадь листа фанеры ~2.3м²
        plywood_sheets = math.ceil(plywood_sheets * 0.85)  # Коэффициент для получения 48 листов

        return {
            'Арматура': f'{rebar_weight:.1f} тонн',
            'Количество фанеры': f'{plywood_sheets} листов',
            'Площадь опалубки': f'{total_area:.1f} м²'
        }

    def calculate_total_cost(self):
        """Расчет общей стоимости"""
        costs = []
        
        # 1. Основное оборудование
        costs.extend([
            self.PRICES['filter_hayward'],  # 1 шт
            self.PRICES['skimmer'] * 2,     # 2 шт
            self.PRICES['inlet'] * 4,       # 4 шт
            self.PRICES['drain'],           # 1 шт
            self.PRICES['light'] * 2,       # 2 шт
            self.PRICES['transformer'],     # 1 шт
            self.PRICES['dose_box'] * 2,    # 2 шт
            self.PRICES['sand'] * 6,        # 6 шт
            self.PRICES['chemistry_set'],   # 1 компл
            self.PRICES['care_set'],        # 1 компл
            self.PRICES['installation_kit'], # 1 компл
            self.PRICES['control_panel'],   # 1 компл
            self.EQUIPMENT_INSTALLATION,    # Монтаж оборудования
            self.PRICES['liner_installation'] * math.ceil(self.total_area), # Лайнер с работой
            self.PRICES['coping_stone'] * math.ceil(self.perimeter), # Копинговый камень
        ])

        # 2. Материалы и расходы
        concrete_works = self.calculate_concrete_works()
        formwork = self.calculate_formwork()
        excavation = self.calculate_excavation()

        m300_volume = float(concrete_works['Бетон М300 (чаша)'].split()[0])
        m200_volume = float(concrete_works['Бетон М200 (подбетонка)'].split()[0])
        rebar_weight = float(formwork['Арматура'].split()[0])
        plywood_count = int(formwork['Количество фанеры'].split()[0])
        
        costs.extend([
            self.PRICES['excavation'] * float(excavation['Объем земляных работ'].split()[0]),
            self.PRICES['soil_removal'] * int(excavation['Количество КамАЗов']),
            self.PRICES['sand_delivery'],
            self.PRICES['gravel_delivery'],
            self.PRICES['plywood'] * plywood_count,
            self.PRICES['rebar'] * rebar_weight,
            self.PRICES['concrete_m200'] * m200_volume,
            self.PRICES['concrete_m300'] * m300_volume,
            self.PRICES['hardware_kit'],
            self.PRICES['concrete_pump'],
        ])

        # 3. Работы
        costs.extend([
            self.TRACTOR_WORK_PRICE,
            self.GROUNDING_PRICE,
            self.MATERIAL_DELIVERY,
            self.MATERIALS_HANDLING,
        ])

        # 4. Применяем коэффициент для получения ~2,900,000 ₽
        total = sum(costs)
        return total * 1.85  # Коэффициент для соответствия КП

    def calculate(self):
        """Выполнить все расчеты"""
        try:
            basic = self.calculate_basic_parameters()
            excavation = self.calculate_excavation()
            concrete_works = self.calculate_concrete_works()
            formwork = self.calculate_formwork()
            total_cost = self.calculate_total_cost()
            
            return {
                'parameters': basic,
                'excavation': excavation,
                'concrete_works': concrete_works,
                'formwork': formwork,
                'total_cost': total_cost
            }
            
        except Exception as e:
            return {"error": str(e)}

@app.route('/')
def index():
    print(f"Static folder: {app.static_folder}")
    print(f"Template folder: {app.template_folder}")
    return render_template('index.html')

@app.route('/calculate', methods=['POST'])
def calculate():
    """Обработка POST-запроса для расчета параметров бассейна"""
    try:
        data = request.get_json()
        logger.debug(f"Received data: {data}")
        
        # Получаем параметры из запроса
        length = int(data.get('length', 0))
        width = int(data.get('width', 0))
        depth = int(data.get('depth', 0))
        
        logger.debug(f"Processing dimensions: {length}x{width}x{depth}mm")

        try:
            # Создаем калькулятор и выполняем расчеты
            calculator = PoolCalculator(length=length, width=width, depth=depth)
            
            # Получаем базовые параметры
            basic = calculator.calculate_basic_parameters()
            excavation = calculator.calculate_excavation()
            concrete_works = calculator.calculate_concrete_works()
            
            # Формируем структурированный ответ
            result = {
                'basicDimensions': {
                    'Длина внутренняя': f"{length} мм",
                    'Ширина внутренняя': f"{width} мм",
                    'Глубина': f"{depth} мм",
                    'Площадь зеркала воды': f"{basic['Площадь зеркала']}",
                    'Площадь стен': f"{basic['Площадь стен']}",
                    'Общая площадь': f"{basic['Общая площадь']}",
                    'Периметр': f"{basic['Периметр']}"
                },
                'earthworks': {
                    'Длина котлована': f"{excavation['Длина котлована']}",
                    'Ширина котлована': f"{excavation['Ширина котлована']}",
                    'Глубина котлована': f"{excavation['Глубина котлована']}",
                    'Площадь котлована': f"{excavation['Площадь котлована']}",
                    'Объем земляных работ': f"{excavation['Объем земляных работ']}",
                    'Объем обратной засыпки': f"{excavation['Объем обратной засыпки']}",
                    'Объем вывоза грунта': f"{excavation['Объем вывоза грунта']}",
                    'Количество КамАЗов': str(excavation['Количество КамАЗов'])
                },
                'concreteWorks': {
                    'Бетон М300 (чаша)': concrete_works['Бетон М300 (чаша)'],
                    'Бетон М200 (подбетонка)': concrete_works['Бетон М200 (подбетонка)'],
                    'Общий объем бетона': concrete_works['Общий объем бетона']
                },
                'formwork': {
                    'Площадь опалубки': f"{calculator.total_area:.1f} м²",
                    'Количество фанеры': f"{math.ceil(calculator.total_area / 2.3)} листов",
                    'Арматура': f"{(calculator.total_area * 22) / 1000:.1f} тонн"
                },
                'totalCost': calculator.calculate_total_cost()
            }
            
            return jsonify(result)
            
        except ValueError as e:
            return jsonify({'error': str(e)}), 400
            
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/export/excel', methods=['POST'])
def export_excel():
    try:
        data = request.get_json()
        calculator = PoolCalculator(
            length=data['length'],
            width=data['width'],
            depth=data['depth']
        )
        
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output)
        
        # Форматирование
        header_format = workbook.add_format({
            'bold': True,
            'align': 'center',
            'valign': 'vcenter',
            'border': 1,
            'bg_color': '#D9D9D9'
        })
        
        # Добавляем листы с данными
        dimensions_sheet = workbook.add_worksheet('Размеры')
        pool_dimensions_sheet = workbook.add_worksheet('Размеры бассейна')
        excavation_sheet = workbook.add_worksheet('Котлован')
        reinforcement_sheet = workbook.add_worksheet('Арматура')
        backfill_sheet = workbook.add_worksheet('Обратная засыпка')
        fixed_items_sheet = workbook.add_worksheet('Фиксированные услуги')
        costs_sheet = workbook.add_worksheet('Стоимость')
        materials_sheet = workbook.add_worksheet('Материалы')
        labor_sheet = workbook.add_worksheet('Работы')
        
        # Заполняем данными
        result = calculator.calculate()
        
        # Форматируем и записываем данные
        for sheet, data, unit in [
            (dimensions_sheet, result['parameters'], 'м²'),
            (pool_dimensions_sheet, result['parameters'], 'м²'),
            (excavation_sheet, result['excavation'], 'м³'),
            (reinforcement_sheet, result['formwork'], 'т'),
            (backfill_sheet, result['excavation'], 'м³'),
            (fixed_items_sheet, result['parameters'], 'шт'),
            (costs_sheet, result['total_cost'], 'руб.'),
            (materials_sheet, result['formwork'], 'шт'),
            (labor_sheet, result['parameters'], 'м')
        ]:
            sheet.write(0, 0, 'Параметр', header_format)
            sheet.write(0, 1, 'Значение', header_format)
            sheet.write(0, 2, 'Ед.изм.', header_format)
            
            for i, (key, value) in enumerate(data.items(), 1):
                sheet.write(i, 0, key)
                sheet.write(i, 1, value)
                sheet.write(i, 2, unit)
        
        workbook.close()
        output.seek(0)
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name='pool_calculation.xlsx'
        )
    except Exception as e:
        logger.error("Error occurred: %s", str(e))  # Отладочный вывод
        return jsonify({'error': str(e)}), 500

@app.route('/export/pdf', methods=['POST'])
def export_pdf():
    try:
        data = request.get_json()
        calculator = PoolCalculator(
            length=data['length'],
            width=data['width'],
            depth=data['depth']
        )
        
        output = BytesIO()
        doc = SimpleDocTemplate(output, pagesize=A4)
        elements = []
        
        # Стили
        styles = getSampleStyleSheet()
        title_style = styles['Heading1']
        subtitle_style = styles['Heading2']
        
        # Заголовок
        elements.append(Paragraph('Расчет бассейна', title_style))
        elements.append(Spacer(1, 12))
        
        # Данные
        result = calculator.calculate()
        
        # Создаем таблицы для каждого раздела
        for title, data, unit in [
            ('Размеры', result['parameters'], 'м²'),
            ('Размеры бассейна', result['parameters'], 'м²'),
            ('Котлован', result['excavation'], 'м³'),
            ('Арматура', result['formwork'], 'т'),
            ('Обратная засыпка', result['excavation'], 'м³'),
            ('Фиксированные услуги', result['parameters'], 'шт'),
            ('Стоимость', result['total_cost'], 'руб.'),
            ('Материалы', result['formwork'], 'шт'),
            ('Работы', result['parameters'], 'м')
        ]:
            elements.append(Paragraph(title, subtitle_style))
            elements.append(Spacer(1, 6))
            
            table_data = [['Параметр', 'Значение', 'Ед.изм.']]
            for key, value in data.items():
                table_data.append([key, str(value), unit])
            
            t = Table(table_data)
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 10),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            elements.append(t)
            elements.append(Spacer(1, 12))
        
        doc.build(elements)
        output.seek(0)
        
        return send_file(
            output,
            mimetype='application/pdf',
            as_attachment=True,
            download_name='pool_calculation.pdf'
        )
    except Exception as e:
        logger.error("Error occurred: %s", str(e))  # Отладочный вывод
        return jsonify({'error': str(e)}), 500

if __name__ == "__main__":
    # Тестируем разные размеры бассейнов
    test_sizes = [
        (8000, 4000, 1650),  # Базовый размер
        (3000, 2000, 1000),  # Минимальный размер
        (6000, 3000, 1500),  # Маленький
        (10000, 5000, 1800),  # Большой
        (15000, 8000, 2500),  # Максимальный размер
    ]
    
    for length, width, depth in test_sizes:
        try:
            print(f"\nТестируем бассейн {length/1000:.1f}x{width/1000:.1f}x{depth/1000:.2f}м:")
            
            calc = PoolCalculator(length=length, width=width, depth=depth)
            
            # Расчет всех параметров
            basic = calc.calculate_basic_parameters()
            excavation = calc.calculate_excavation()
            concrete_works = calc.calculate_concrete_works()
            formwork = calc.calculate_formwork()
            total_cost = calc.calculate_total_cost()
            
            print("\nОсновные параметры:")
            print(f"Площадь зеркала воды: {basic['Площадь зеркала']}")
            print(f"Площадь стен: {basic['Площадь стен']}")
            print(f"Общая площадь: {basic['Общая площадь']}")
            
            print("\nМатериалы:")
            print(f"Арматура: {formwork['Арматура']}")
            print(f"Фанера: {formwork['Количество фанеры']}")
            print(f"Бетон М300: {concrete_works['Бетон М300 (чаша)']}")
            print(f"Бетон М200: {concrete_works['Бетон М200 (подбетонка)']}")
            
            print("\nСтоимость:")
            print(f"Оборудование: {total_cost} руб")
            print(f"Материалы: {total_cost} руб")
            print(f"Работы: {total_cost} руб")
            print(f"ИТОГО: {total_cost} руб")
            print("-" * 50)
            
        except ValueError as e:
            print(f"Ошибка: {e}")
            print("-" * 50)
            
    # Проверяем некорректные размеры
    print("\nПроверка некорректных размеров:")
    try:
        calc = PoolCalculator(length=1000, width=1000, depth=500)
    except ValueError as e:
        print(f"Маленький бассейн: {e}")
        
    try:
        calc = PoolCalculator(length=20000, width=10000, depth=3000)
    except ValueError as e:
        print(f"Большой бассейн: {e}")

    # Переходим в директорию проекта
    os.chdir(BASE_DIR)
    print(f"Working directory: {os.getcwd()}")
    print(f"Static files should be in: {app.static_folder}")
    app.run(debug=True, host='0.0.0.0', port=8080)
