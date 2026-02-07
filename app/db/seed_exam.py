"""
Seed script para poblar las tablas exam_categories y exam_questions.

Ejecutar con:
    python -m app.db.seed_exam
"""
from app.db.base import Base
from app.db.session import engine, SessionLocal
from app.models.exam import ExamCategory, ExamQuestion


# ── Definición de categorías ─────────────────────────────────────────────────
CATEGORIES = [
    {"name": "Seguridad",  "color": "red",   "display_order": 1, "questions_to_show": 10, "min_score_percent": 80},
    {"name": "Inocuidad",  "color": "blue",  "display_order": 2, "questions_to_show": 10, "min_score_percent": 80},
    {"name": "Ambiental",  "color": "green", "display_order": 3, "questions_to_show": 10, "min_score_percent": 80},
]

# ── Definición de las 75 preguntas ───────────────────────────────────────────
# Cada entrada: (category_name, question_text, [options], correct_answer)

QUESTIONS = [
    # ═══════════════════════════════════════════
    # SEGURIDAD  (25 preguntas)
    # ═══════════════════════════════════════════
    (
        "Seguridad",
        "¿Cuál de las siguientes opciones describe mejor el concepto de 'Riesgo' en el contexto de la seguridad industrial?",
        [
            "Una fuente o situación con potencial de causar daño.",
            "Un suceso relacionado con el trabajo donde ocurre o podría ocurrir un daño.",
            "Cualquier condición que ha sido evaluada y declarada libre de peligros.",
            "La combinación de la probabilidad de que ocurra un suceso y la consecuencia del mismo.",
        ],
        "La combinación de la probabilidad de que ocurra un suceso y la consecuencia del mismo.",
    ),
    (
        "Seguridad",
        "Según la clasificación de eventos de Coca-Cola FEMSA, un incidente que resulta en fatalidades o lesiones serias (SIF) se clasifica internamente como:",
        ["Nivel 1", "Nivel 3", "Nivel 0", "Nivel 2"],
        "Nivel 3",
    ),
    (
        "Seguridad",
        "¿Cuál es el propósito principal del procedimiento LOTO (Bloqueo y Etiquetado) mencionado en las 'Reglas para salvar vidas'?",
        [
            "Confirmar que no hay energía presente o está aislada antes de intervenir un equipo.",
            "Protegerse contra caídas cuando se trabaja en altura.",
            "Verificar que el personal tenga las habilidades adecuadas para la tarea.",
            "Asegurar que los contratistas tengan el permiso de trabajo adecuado.",
        ],
        "Confirmar que no hay energía presente o está aislada antes de intervenir un equipo.",
    ),
    (
        "Seguridad",
        "¿Qué elemento del Equipo de Protección Personal (EPP) de categoría ESPECIAL es fundamental para un trabajo de soldadura?",
        ["Guantes de carnaza", "Botas industriales con casquillo", "Chaleco de alta visibilidad", "Careta para soldar"],
        "Careta para soldar",
    ),
    (
        "Seguridad",
        "De acuerdo con la normativa para el levantamiento manual de cargas, ¿cuál es la masa máxima que un trabajador masculino de 35 años puede levantar?",
        ["25 kg", "15 kg", "7 kg", "20 kg"],
        "25 kg",
    ),
    (
        "Seguridad",
        "Según las categorías de riesgo para las actividades de contratistas, ¿cómo se clasifica una tarea que implica trabajos de construcción o demolición?",
        ["Riesgo Ad Hoc", "Riesgo Alto", "Riesgo Bajo", "Riesgo Medio"],
        "Riesgo Alto",
    ),
    (
        "Seguridad",
        "Durante una situación de emergencia en las instalaciones, ¿qué acción se debe tomar si se escucha un sonido de alarma continuo?",
        [
            "Buscar al supervisor para confirmar si la emergencia es real.",
            "Permanecer alerta y esperar instrucciones adicionales.",
            "Detener el trabajo y apagar únicamente los equipos de cómputo.",
            "Dirigirse al punto de reunión más cercano de manera ordenada.",
        ],
        "Dirigirse al punto de reunión más cercano de manera ordenada.",
    ),
    (
        "Seguridad",
        "Para realizar trabajos en calor, como corte y soldadura, ¿cuál es el número mínimo de personas requeridas y cuáles son sus roles?",
        [
            "Dos personas: el ejecutor que realiza el trabajo y el monitor que vigila.",
            "Tres personas: ejecutor, monitor y un supervisor de KOF.",
            "Una sola persona, siempre que esté debidamente capacitada.",
            "No se especifica un número, solo se requiere un extintor cerca.",
        ],
        "Dos personas: el ejecutor que realiza el trabajo y el monitor que vigila.",
    ),
    (
        "Seguridad",
        "De acuerdo con las normas de seguridad para el 'joggeo' de maquinaria, ¿qué práctica está estrictamente prohibida?",
        [
            "Que una persona accione el control mientras otra persona interviene el equipo.",
            "Realizar el joggeo a una velocidad reducida al 50% o inferior.",
            "Notificar al personal del área antes de iniciar el joggeo.",
            "Realizar el joggeo con las guardas de seguridad físicas correctamente colocadas.",
        ],
        "Que una persona accione el control mientras otra persona interviene el equipo.",
    ),
    (
        "Seguridad",
        "Al utilizar una escalera de extensión para acceder a un nivel superior, esta debe sobrepasar el punto de apoyo. ¿Cuál es la distancia mínima requerida?",
        [
            "Debe estar exactamente al mismo nivel que el punto de acceso.",
            "La escalera no debe sobrepasar el punto de acceso para evitar tropiezos.",
            "Debe sobrepasar 50 cm.",
            "Debe sobrepasar 91 cm.",
        ],
        "Debe sobrepasar 91 cm.",
    ),
    (
        "Seguridad",
        "¿Cuál es la definición correcta de 'Peligro' según el curso de inducción de Coca-Cola FEMSA?",
        [
            "La combinación de la probabilidad y las consecuencias de un suceso específico.",
            "Un suceso relacionado con el trabajo en el que ocurre o podría ocurrir un daño físico.",
            "Fuente o situación potencial de daño en términos de lesiones o efectos negativos para la salud.",
            "La implementación de controles para mitigar la probabilidad de un accidente.",
        ],
        "Fuente o situación potencial de daño en términos de lesiones o efectos negativos para la salud.",
    ),
    (
        "Seguridad",
        "En la metodología IPERC, ¿cuáles son los tres criterios principales para evaluar el riesgo?",
        [
            "Peligro, Consecuencia y Control.",
            "Gravedad, Exposición y Frecuencia.",
            "Costo, Tiempo y Calidad.",
            "Probabilidad, Impacto y Mitigación.",
        ],
        "Probabilidad, Impacto y Mitigación.",
    ),
    (
        "Seguridad",
        "De acuerdo con la clasificación de eventos, ¿qué significa la sigla SIF?",
        [
            "Incidentes Serios o Fatalidades (Serious Injuries or Fatalities).",
            "Seguridad Industrial y de Fuego.",
            "Situaciones de Incidentes Frecuentes.",
            "Sistema de Inspección de Fábricas.",
        ],
        "Incidentes Serios o Fatalidades (Serious Injuries or Fatalities).",
    ),
    (
        "Seguridad",
        "Según la NOM-036-1-STPS-2018, ¿cuál es la masa máxima que puede levantar un trabajador masculino entre 18 y 45 años?",
        ["15 kg", "50 kg", "20 kg", "25 kg"],
        "25 kg",
    ),
    (
        "Seguridad",
        "Para trabajos con equipo de oxicorte (oxiacetileno), ¿a qué distancia mínima deben colocarse los cilindros del lugar de corte?",
        ["15 metros", "11 metros", "3 metros", "6 metros"],
        "6 metros",
    ),
    (
        "Seguridad",
        "¿Cuál es la función principal de un dispositivo GFCI según el curso?",
        [
            "Aumentar el voltaje para herramientas pesadas.",
            "Regular la temperatura de los tableros eléctricos.",
            "Protección contra choques eléctricos mediante la detección de fallas a tierra.",
            "Permitir la conexión de múltiples adaptadores en un solo enchufe.",
        ],
        "Protección contra choques eléctricos mediante la detección de fallas a tierra.",
    ),
    (
        "Seguridad",
        "Bajo la Regla para Salvar Vidas número 8 (Trabajo Seguro en Sistemas Energizados), ¿cuál es el procedimiento obligatorio?",
        [
            "Procedimiento LOTO (Bloqueo y Etiquetado) para asegurar cero tensión.",
            "Mantener una distancia de 1 metro de los cables.",
            "Uso de guantes de carnaza y lentes de seguridad.",
            "Solicitar autorización verbal al jefe de área.",
        ],
        "Procedimiento LOTO (Bloqueo y Etiquetado) para asegurar cero tensión.",
    ),
    (
        "Seguridad",
        "¿Cómo se define a un 'Contratista Regular' según la frecuencia de su trabajo?",
        [
            "Aquel que labora diariamente en el sitio reportando al personal de la instalación.",
            "Realiza trabajos en el sitio una vez o menos en seis meses.",
            "Realiza trabajos en el sitio más de una vez en seis meses.",
            "Contratado para una única tarea o proyecto específico.",
        ],
        "Realiza trabajos en el sitio más de una vez en seis meses.",
    ),
    (
        "Seguridad",
        "En caso de emergencia, ¿qué indica un sonido de alarma CONTINUO?",
        [
            "Situación de Alerta (estar prevenidos).",
            "Fin de la emergencia y retorno seguro.",
            "Prueba de sistema de altavoces.",
            "Situación de Emergencia y evacuación inmediata del área.",
        ],
        "Situación de Emergencia y evacuación inmediata del área.",
    ),
    (
        "Seguridad",
        "Para trabajos en alturas, ¿a partir de qué altura es obligatorio el uso de arnés de seguridad con línea de vida?",
        ["1.20 metros", "1.80 metros", "2.50 metros", "1.50 metros"],
        "1.80 metros",
    ),
    (
        "Seguridad",
        "De acuerdo con el código de vestimenta para proveedores/ejecutores, ¿de qué color debe ser el casco de seguridad?",
        ["Verde", "Amarillo", "Rojo", "Blanco"],
        "Amarillo",
    ),
    (
        "Seguridad",
        "¿Cuál de las siguientes es una prohibición estricta durante el proceso de 'Joggeo' (posicionamiento) de maquinaria?",
        [
            "Realizar el joggeo mientras otra persona interviene físicamente el equipo.",
            "Notificar al personal del área antes de iniciar.",
            "Reducir la velocidad del motor al 50%.",
            "Que la misma persona que controla el mando sea quien ejecute la actividad.",
        ],
        "Realizar el joggeo mientras otra persona interviene físicamente el equipo.",
    ),
    (
        "Seguridad",
        "En el procedimiento LOTO, ¿cuál es el paso final antes de considerar que el bloqueo es efectivo?",
        [
            "Colocar la tarjeta de aviso.",
            "Cerciorar la efectividad del bloqueo mediante una prueba de arranque.",
            "Drenar las energías almacenadas.",
            "Firmar el permiso de trabajo.",
        ],
        "Cerciorar la efectividad del bloqueo mediante una prueba de arranque.",
    ),
    (
        "Seguridad",
        "¿Cuál es el tiempo máximo de confirmación de una emergencia antes de proceder con el aviso masivo?",
        ["1 minuto", "5 minutos", "10 minutos", "2 minutos"],
        "2 minutos",
    ),
    (
        "Seguridad",
        "¿Qué requisito debe cumplir un extintor para ser aceptado en un frente de trabajo de un contratista?",
        [
            "Haber sido recargado en la última semana.",
            "No tener manómetro para evitar fugas.",
            "Tener el nombre de la compañía contratista rotulado de forma permanente.",
            "Debe ser de tipo CO2 obligatoriamente.",
        ],
        "Tener el nombre de la compañía contratista rotulado de forma permanente.",
    ),

    # ═══════════════════════════════════════════
    # INOCUIDAD  (25 preguntas)
    # ═══════════════════════════════════════════
    (
        "Inocuidad",
        "¿Qué se entiende por Inocuidad Alimentaria?",
        [
            "Que el producto tenga buen sabor",
            "Que el producto cumpla con requisitos comerciales",
            "Que el producto y/o alimento no haga daño a la salud",
            "Que el producto tenga buena presentación",
        ],
        "Que el producto y/o alimento no haga daño a la salud",
    ),
    (
        "Inocuidad",
        "¿Qué sistema de certificación implementa Coca-Cola FEMSA para garantizar la inocuidad de sus productos?",
        ["ISO 9001", "HACCP", "FSSC 22000", "Industria Limpia"],
        "FSSC 22000",
    ),
    (
        "Inocuidad",
        "¿Qué normas conforman el esquema FSSC 22000?",
        [
            "ISO 14001, ISO 45001 y NOM-051",
            "ISO 22000, ISO/TS 22002-1 y requisitos adicionales de FSSC 22000",
            "HACCP y BPM",
            "ISO 9001 y ISO 14001",
        ],
        "ISO 22000, ISO/TS 22002-1 y requisitos adicionales de FSSC 22000",
    ),
    (
        "Inocuidad",
        "¿Qué es un peligro de inocuidad alimentaria según ISO 22000?",
        [
            "Cualquier situación incómoda para el consumidor",
            "Un agente biológico, químico o físico con potencial de causar daño a la salud",
            "Un error en el proceso productivo",
            "Un incumplimiento legal",
        ],
        "Un agente biológico, químico o físico con potencial de causar daño a la salud",
    ),
    (
        "Inocuidad",
        "¿Cuál de los siguientes es un ejemplo de peligro físico?",
        ["Detergentes", "Bacterias", "Vidrio", "Insecticidas"],
        "Vidrio",
    ),
    (
        "Inocuidad",
        "¿Qué son los Pre-requisitos (PPR) en Inocuidad Alimentaria?",
        [
            "Actividades opcionales para mejorar la calidad",
            "Condiciones y actividades básicas para mantener un ambiente higiénico",
            "Auditorías externas",
            "Indicadores de desempeño",
        ],
        "Condiciones y actividades básicas para mantener un ambiente higiénico",
    ),
    (
        "Inocuidad",
        "¿Cuál de las siguientes acciones corresponde a los Buenos Hábitos de Manufactura?",
        [
            "Usar joyería en áreas de proceso",
            "Consumir alimentos en cualquier área",
            "Usar correctamente cofia y cubrebocas",
            "Masticar chicle en planta",
        ],
        "Usar correctamente cofia y cubrebocas",
    ),
    (
        "Inocuidad",
        "¿Cuál es el objetivo del Manejo Integral de Plagas?",
        [
            "Eliminar todas las plagas con químicos",
            "Minimizar impactos a los procesos y garantizar productos seguros",
            "Mantener limpias solo las áreas externas",
            "Usar únicamente trampas mecánicas",
        ],
        "Minimizar impactos a los procesos y garantizar productos seguros",
    ),
    (
        "Inocuidad",
        "¿Qué acción ayuda a prevenir la contaminación cruzada?",
        [
            "Usar los mismos utensilios en todas las áreas",
            "Respetar rutas de tránsito del personal",
            "Mezclar ingredientes sin identificación",
            "Ignorar monitoreos ambientales",
        ],
        "Respetar rutas de tránsito del personal",
    ),
    (
        "Inocuidad",
        "¿Qué se debe hacer si se detecta personal no autorizado en áreas críticas?",
        [
            "No hacer nada",
            "Confrontarlo directamente",
            "Reportarlo inmediatamente al encargado del área de trabajo",
            "Retirarse del área",
        ],
        "Reportarlo inmediatamente al encargado del área de trabajo",
    ),
    (
        "Inocuidad",
        "¿Qué se entiende por el término 'Inocuidad' según los estándares de Coca-Cola FEMSA?",
        [
            "La capacidad de la planta para producir sin generar residuos químicos en el drenaje.",
            "La garantía de que un producto o alimento no causará daño a la salud del consumidor.",
            "El cumplimiento estricto de los niveles de azúcar y gas en cada botella producida.",
            "La certificación que asegura que el envase es 100% reciclable y seguro para el ambiente.",
        ],
        "La garantía de que un producto o alimento no causará daño a la salud del consumidor.",
    ),
    (
        "Inocuidad",
        "¿Cuál es el sistema de Certificación de Inocuidad Alimentaria utilizado por la compañía?",
        ["ISO 14001", "FSSC 22000", "ISO 45001", "NOM-036-STPS"],
        "FSSC 22000",
    ),
    (
        "Inocuidad",
        "En el contexto de peligros de inocuidad, ¿cuál de los siguientes es un ejemplo de un peligro biológico?",
        [
            "Bacterias como Salmonella o Escherichia Coli.",
            "Residuos de lubricantes o detergentes en la línea.",
            "Fragmentos de vidrio provenientes de botellas rotas.",
            "Presencia de alérgenos como la soya o el trigo.",
        ],
        "Bacterias como Salmonella o Escherichia Coli.",
    ),
    (
        "Inocuidad",
        "¿Qué tipo de peligro de inocuidad representan las astillas de madera o los pedazos de metal encontrados en un producto?",
        [
            "Peligros Físicos",
            "Peligros Biológicos",
            "Peligros Ergonómicos",
            "Peligros Químicos",
        ],
        "Peligros Físicos",
    ),
    (
        "Inocuidad",
        "¿Cuál es la política correcta sobre el uso de objetos personales en las áreas de producción y almacenes?",
        [
            "Está prohibido el uso de joyería, relojes, piercings o botones arriba de la cintura.",
            "Se pueden portar plumas en las orejas para facilitar el registro de datos rápidamente.",
            "Solo se permite el uso de relojes si son necesarios para cronometrar procesos de limpieza.",
            "Se permite el uso de anillos de matrimonio siempre que estén cubiertos con guantes.",
        ],
        "Está prohibido el uso de joyería, relojes, piercings o botones arriba de la cintura.",
    ),
    (
        "Inocuidad",
        "¿Qué debe hacer un colaborador si presenta síntomas como vómito, diarrea o heridas abiertas antes de iniciar su jornada?",
        [
            "Reportar inmediatamente su estado de salud al servicio médico o a su jefe directo.",
            "Cubrir las heridas con cinta industrial y continuar trabajando para no afectar la productividad.",
            "Tomar un medicamento por cuenta propia y evitar comentarlo para no ser enviado a casa.",
            "Ingresar a las áreas de proceso usando un cubrebocas doble para compensar los síntomas.",
        ],
        "Reportar inmediatamente su estado de salud al servicio médico o a su jefe directo.",
    ),
    (
        "Inocuidad",
        "¿Cuál es el objetivo principal del programa de 'Defensa de los Alimentos' (Food Defense)?",
        [
            "Asegurar que el producto tenga un sabor consistente en todas las unidades operativas.",
            "Detectar y eliminar ataques maliciosos intencionados como sabotaje o bioterrorismo.",
            "Capacitar a los brigadistas en el uso de extintores para proteger las bodegas de insumos.",
            "Garantizar que los proveedores entreguen materias primas con certificados de calidad.",
        ],
        "Detectar y eliminar ataques maliciosos intencionados como sabotaje o bioterrorismo.",
    ),
    (
        "Inocuidad",
        "En la rotación de existencias en almacenes, ¿qué principio asegura que el producto que vence primero sea el primero en salir?",
        [
            "FEFO (First Expired, First Out)",
            "JIT (Just In Time)",
            "LIFO (Last In, First Out)",
            "FIFO (First In, First Out)",
        ],
        "FEFO (First Expired, First Out)",
    ),
    (
        "Inocuidad",
        "¿Cuál de los siguientes grupos representa alérgenos comunes que deben controlarse para evitar la contaminación cruzada?",
        [
            "Sal, ácido cítrico y saborizantes naturales.",
            "Carne de res, pollo, arroz y zanahorias.",
            "Leche, huevos, pescado, nueces y soya.",
            "Agua, dióxido de carbono y jarabe de alta fructosa.",
        ],
        "Leche, huevos, pescado, nueces y soya.",
    ),
    (
        "Inocuidad",
        "¿Cómo debe ser el manejo de los utensilios de limpieza para evitar la contaminación cruzada microbiológica?",
        [
            "Lavar todos los utensilios con agua caliente una vez al mes para desinfectarlos.",
            "Guardar los utensilios de limpieza dentro de las salas de jarabes para tenerlos a la mano.",
            "Utilizar utensilios que sigan un código de colores definido para cada área específica.",
            "Compartir los mismos trapeadores en todas las áreas para optimizar el recurso de limpieza.",
        ],
        "Utilizar utensilios que sigan un código de colores definido para cada área específica.",
    ),
    (
        "Inocuidad",
        "En relación al Manejo Integral de Plagas, ¿cuál es una responsabilidad directa del personal operativo?",
        [
            "Mover las trampas de roedores para que no estorben durante las maniobras de carga.",
            "Limpiar con agua a presión el interior de las lámparas de luz UV para eliminar insectos.",
            "Aplicar insecticidas químicos personalmente cuando vean un insecto en su área.",
            "Mantener las puertas de acceso cerradas y reportar cualquier avistamiento de plaga.",
        ],
        "Mantener las puertas de acceso cerradas y reportar cualquier avistamiento de plaga.",
    ),
    (
        "Inocuidad",
        "¿Qué requisito adicional de la versión 6 de FSSC 22000 se enfoca en prevenir la alteración o sustitución intencionada de alimentos por razones económicas?",
        [
            "Prevención del Fraude Alimentario",
            "Gestión de los Servicios",
            "Control de Calidad",
            "Cultura de Inocuidad",
        ],
        "Prevención del Fraude Alimentario",
    ),
    (
        "Inocuidad",
        "¿Cuál es una medida obligatoria de higiene personal para quienes ingresan a zonas de proceso con vello facial (barba o bigote)?",
        [
            "Aplicarse gel fijador para asegurar que el vello no se desprenda durante la jornada.",
            "Solo es necesario usar cubrebocas normal si el bigote es corto.",
            "Usar una protección limpia (cubrebaba) que cubra totalmente el vello facial.",
            "Recortar el vello facial al menos una vez por semana como única medida.",
        ],
        "Usar una protección limpia (cubrebaba) que cubra totalmente el vello facial.",
    ),
    (
        "Inocuidad",
        "En el control de químicos, ¿qué se debe verificar respecto a los productos de calderas y aceites de compresores en áreas de proceso?",
        [
            "Que sean obligatoriamente de grado alimenticio.",
            "Que tengan el color más llamativo posible para detectar fugas rápidamente.",
            "Que sean almacenados junto a los ingredientes para facilitar su aplicación.",
            "Que no tengan olor para que el personal no se distraiga durante la operación.",
        ],
        "Que sean obligatoriamente de grado alimenticio.",
    ),
    (
        "Inocuidad",
        "De acuerdo con los Buenos Hábitos de Manufactura, ¿qué acción está prohibida respecto al consumo de alimentos y bebidas?",
        [
            "Consumir alimentos, mascar chicle o fumar dentro de las áreas operativas.",
            "Tomar agua exclusivamente en vasos de vidrio transparentes cerca de la línea.",
            "Mascar chicle siempre y cuando se use el cubrebocas correctamente colocado.",
            "Guardar el almuerzo dentro de los lockers de herramientas para ahorrar tiempo.",
        ],
        "Consumir alimentos, mascar chicle o fumar dentro de las áreas operativas.",
    ),

    # ═══════════════════════════════════════════
    # AMBIENTAL  (25 preguntas)
    # ═══════════════════════════════════════════
    (
        "Ambiental",
        "¿Cuál es la definición correcta de medio ambiente según la presentación?",
        [
            "El entorno natural sin intervención humana",
            "Únicamente el aire, agua y suelo",
            "El entorno en el cual una planta opera, incluyendo aire, agua, suelo, recursos naturales, flora, fauna, seres humanos y sus interrelaciones",
            "Solo el área externa de la unidad operativa",
        ],
        "El entorno en el cual una planta opera, incluyendo aire, agua, suelo, recursos naturales, flora, fauna, seres humanos y sus interrelaciones",
    ),
    (
        "Ambiental",
        "¿Qué es la certificación ISO 14001?",
        [
            "Un programa exclusivo para residuos peligrosos",
            "Una norma que regula únicamente el consumo de agua",
            "Una norma internacional que apoya la protección ambiental y la prevención de la contaminación",
            "Un plan de reciclaje obligatorio",
        ],
        "Una norma internacional que apoya la protección ambiental y la prevención de la contaminación",
    ),
    (
        "Ambiental",
        "¿Cuáles son los principales aspectos ambientales identificados en la unidad operativa?",
        [
            "Ruido, iluminación y temperatura",
            "Agua, energía, residuos y aire",
            "Clima, fauna y suelo",
            "Transporte y tráfico",
        ],
        "Agua, energía, residuos y aire",
    ),
    (
        "Ambiental",
        "¿Qué es la Matriz de Aspectos e Impactos Ambientales (MAIA)?",
        [
            "Un listado de residuos peligrosos",
            "Una herramienta para evaluar proveedores",
            "Un instrumento para identificar y evaluar aspectos e impactos ambientales",
            "Un plan de emergencias ambientales",
        ],
        "Un instrumento para identificar y evaluar aspectos e impactos ambientales",
    ),
    (
        "Ambiental",
        "¿Cuál de los siguientes es un residuo orgánico según la clasificación KOF?",
        [
            "Latas de aluminio",
            "Botellas de vidrio",
            "Restos de comida sin envoltura",
            "Envases PET",
        ],
        "Restos de comida sin envoltura",
    ),
    (
        "Ambiental",
        "¿Qué significa la sigla CRETIB en residuos peligrosos?",
        [
            "Corrosivo, Reactivo, Explosivo, Tóxico, Inflamable y Biológico-Infeccioso",
            "Contaminante, Reciclable, Ecológico, Tóxico, Inflamable y Biológico",
            "Corrosivo, Residual, Explosivo, Tóxico, Inflamable y Básico",
            "Químico, Reactivo, Explosivo, Tóxico, Inflamable y Biológico",
        ],
        "Corrosivo, Reactivo, Explosivo, Tóxico, Inflamable y Biológico-Infeccioso",
    ),
    (
        "Ambiental",
        "¿Cuál de los siguientes residuos se considera peligroso?",
        [
            "Papel y cartón",
            "Restos de jardinería",
            "Aceite contaminado con amoniaco",
            "Botellas de vidrio",
        ],
        "Aceite contaminado con amoniaco",
    ),
    (
        "Ambiental",
        "¿Qué práctica ayuda al uso eficiente de la energía?",
        [
            "Dejar encendidos los equipos en espera",
            "Apagar motores y transportadores cuando no estén en uso",
            "Usar más ventiladores",
            "Mantener enchufes conectados",
        ],
        "Apagar motores y transportadores cuando no estén en uso",
    ),
    (
        "Ambiental",
        "¿Cuál es una buena práctica para prevenir la contaminación de aguas residuales?",
        [
            "Depositar sólidos pequeños en el drenaje",
            "Derramar aceites en coladeras",
            "Utilizar charolas de contención durante mantenimientos",
            "Lavar envases químicos en lavabos",
        ],
        "Utilizar charolas de contención durante mantenimientos",
    ),
    (
        "Ambiental",
        "¿Qué debe hacerse en caso de un derrame de material peligroso?",
        [
            "Limpiarlo sin notificar",
            "Ignorarlo si es pequeño",
            "Notificar al encargado del área para activar el protocolo con personal capacitado",
            "Esperar a que se evapore",
        ],
        "Notificar al encargado del área para activar el protocolo con personal capacitado",
    ),
    (
        "Ambiental",
        "¿Cuál es el objetivo principal del programa de certificación 'Residuo Cero' en las plantas de Coca-Cola FEMSA?",
        [
            "Prohibir el uso de cualquier material plástico dentro de las instalaciones.",
            "Valorizar los residuos para evitar que terminen en rellenos sanitarios.",
            "Incentivar la incineración de todos los desechos para generar calor.",
            "Reducir los costos de producción mediante la compra de insumos usados.",
        ],
        "Valorizar los residuos para evitar que terminen en rellenos sanitarios.",
    ),
    (
        "Ambiental",
        "De acuerdo con los conceptos de la norma ISO 14001, ¿qué representa un 'Aspecto Ambiental'?",
        [
            "Una ley obligatoria emitida por el gobierno federal.",
            "Elemento de las actividades o productos que interactúa con el medio ambiente.",
            "El daño económico causado por un desastre natural.",
            "El efecto o cambio resultante en el medio ambiente.",
        ],
        "Elemento de las actividades o productos que interactúa con el medio ambiente.",
    ),
    (
        "Ambiental",
        "¿Qué siglas se utilizan para identificar las características que definen a un residuo como peligroso?",
        ["CRETI", "MAIA", "ASPECTO", "CRETIB"],
        "CRETIB",
    ),
    (
        "Ambiental",
        "En el manejo de materiales peligrosos, ¿qué capacidad mínima debe tener un dique de contención secundaria?",
        [
            "El 50% del volumen total almacenado en el área.",
            "Exactamente el 100% de la suma de todos los contenedores.",
            "El 110% del volumen del contenedor más grande del área.",
            "Un volumen estándar de 200 litros para cualquier sustancia.",
        ],
        "El 110% del volumen del contenedor más grande del área.",
    ),
    (
        "Ambiental",
        "¿En qué categoría se deben clasificar los residuos de 'emplaye' (película plástica) y fleje según los lineamientos de la compañía?",
        [
            "Plásticos / Emplaye.",
            "Papel y Cartón.",
            "Residuos de Manejo Especial.",
            "Inorgánicos generales.",
        ],
        "Plásticos / Emplaye.",
    ),
    (
        "Ambiental",
        "¿Cuál de los siguientes es un ejemplo de un 'Impacto Ambiental' según la capacitación?",
        [
            "Consumo de combustibles fósiles.",
            "Generación de emisiones a la atmósfera.",
            "Contaminación del agua.",
            "Uso de energía renovable.",
        ],
        "Contaminación del agua.",
    ),
    (
        "Ambiental",
        "¿Cuál es una práctica prohibida en el manejo de aguas residuales para evitar la contaminación de drenajes?",
        [
            "Separar los residuos sólidos de las rejillas de drenaje.",
            "Depositar únicamente agua de limpieza de pisos.",
            "Verter aceites, grasas o químicos en coladeras y lavabos.",
            "Instalar charolas de contención en áreas de mantenimiento.",
        ],
        "Verter aceites, grasas o químicos en coladeras y lavabos.",
    ),
    (
        "Ambiental",
        "¿Cómo se determina la prioridad de un aspecto ambiental en la matriz MAIA?",
        [
            "Multiplicando la Probabilidad por la Magnitud (Impacto + Entorno).",
            "Basándose únicamente en la opinión del gerente de planta.",
            "Contando el número de quejas recibidas de la comunidad.",
            "Sumando el volumen de residuos generados por mes.",
        ],
        "Multiplicando la Probabilidad por la Magnitud (Impacto + Entorno).",
    ),
    (
        "Ambiental",
        "¿Qué documento es estrictamente necesario para el ingreso y manejo de cualquier sustancia química por parte de un contratista?",
        [
            "Una fotografía del envase original del proveedor.",
            "El manual de operación del equipo que utilizará el químico.",
            "La factura de compra que demuestre que el producto es nuevo.",
            "La Hoja de Datos de Seguridad (HDS) con pictogramas correspondientes.",
        ],
        "La Hoja de Datos de Seguridad (HDS) con pictogramas correspondientes.",
    ),
    (
        "Ambiental",
        "Dentro de la clasificación de residuos peligrosos generados en mantenimiento, ¿en qué categoría entran las lámparas y balastros usados?",
        [
            "Vidrio común.",
            "Chatarra metálica.",
            "Inorgánicos no reciclables.",
            "Residuos Peligrosos.",
        ],
        "Residuos Peligrosos.",
    ),
    (
        "Ambiental",
        "¿Cuál es la norma oficial mexicana que establece el procedimiento para identificar y clasificar los residuos peligrosos?",
        [
            "NOM-001-SEMARNAT-2021",
            "NOM-085-SEMARNAT-2011",
            "NOM-081-SEMARNAT-1994",
            "NOM-052-SEMARNAT-2005",
        ],
        "NOM-052-SEMARNAT-2005",
    ),
    (
        "Ambiental",
        "En el uso eficiente de la energía, ¿cuál de las siguientes acciones es responsabilidad del personal operativo y contratista?",
        [
            "Eliminar los sensores de movimiento de las luminarias para que siempre haya luz.",
            "Modificar la programación de los PLC para acelerar la producción.",
            "Reportar fugas de aire comprimido y apagar equipos que no estén en uso.",
            "Aumentar la temperatura de los aires acondicionados al máximo en verano.",
        ],
        "Reportar fugas de aire comprimido y apagar equipos que no estén en uso.",
    ),
    (
        "Ambiental",
        "¿Qué se debe hacer con los residuos de comida y restos de jardinería?",
        [
            "Colocarlos en el área de chatarra para su retiro.",
            "Depositarlos en el contenedor de Residuos Orgánicos.",
            "Mezclarlos con el papel y cartón para su degradación.",
            "Incinerarlos en un área abierta de la planta.",
        ],
        "Depositarlos en el contenedor de Residuos Orgánicos.",
    ),
    (
        "Ambiental",
        "¿Cuál es la función del Almacén Temporal de Residuos Peligrosos (ATRP)?",
        [
            "Almacenar el exceso de producto terminado para la venta.",
            "Funcionar como comedor alterno para el personal de limpieza.",
            "Resguardar los residuos peligrosos de forma segura hasta su recolección oficial.",
            "Servir como depósito final donde los residuos se quedan permanentemente.",
        ],
        "Resguardar los residuos peligrosos de forma segura hasta su recolección oficial.",
    ),
    (
        "Ambiental",
        "¿Cómo contribuye el correcto re-abastecimiento y reutilización de agua a la sostenibilidad del negocio?",
        [
            "Es un requisito que solo aplica si la planta se queda sin presupuesto.",
            "Disminuye la explotación de recursos naturales y asegura el abasto futuro.",
            "Aumenta el sabor del producto final mediante el uso de agua reciclada.",
            "Permite que la planta funcione sin necesidad de permisos legales.",
        ],
        "Disminuye la explotación de recursos naturales y asegura el abasto futuro.",
    ),
]


def seed():
    """Crea las tablas (si no existen) e inserta categorías y preguntas."""
    # 1. Crear tablas
    Base.metadata.create_all(bind=engine)
    print("Tablas creadas / verificadas.")

    db = SessionLocal()
    try:
        # 2. Insertar categorías (get_or_create)
        cat_map: dict[str, ExamCategory] = {}
        for cat_data in CATEGORIES:
            existing = db.query(ExamCategory).filter_by(name=cat_data["name"]).first()
            if existing:
                cat_map[cat_data["name"]] = existing
                print(f"  Categoría '{cat_data['name']}' ya existe (id={existing.id}).")
            else:
                cat = ExamCategory(**cat_data)
                db.add(cat)
                db.flush()
                cat_map[cat_data["name"]] = cat
                print(f"  Categoría '{cat_data['name']}' creada (id={cat.id}).")

        # 3. Insertar preguntas (skip si ya existe por texto)
        inserted = 0
        skipped = 0
        for cat_name, q_text, options, correct in QUESTIONS:
            exists = (
                db.query(ExamQuestion)
                .filter_by(question_text=q_text)
                .first()
            )
            if exists:
                skipped += 1
                continue
            question = ExamQuestion(
                category_id=cat_map[cat_name].id,
                question_text=q_text,
                options=options,
                correct_answer=correct,
            )
            db.add(question)
            inserted += 1

        db.commit()
        print(f"\nSeed completado: {inserted} preguntas insertadas, {skipped} ya existían.")
        print(f"Total categorías: {len(cat_map)}")
        total_q = db.query(ExamQuestion).count()
        print(f"Total preguntas en BD: {total_q}")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
