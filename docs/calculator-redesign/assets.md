# Ресурсы конфигуратора

## Генерация

ImageGen встроенного инструмента, 04.11.2026. Изображения — объясняющие иллюстрации, не реальные объекты компании и не сертификат определённой марки материала. В интерфейсе предпросмотра есть явная подпись об ИИ. В карточках материал назван как группа, выбранная в действующем ассортименте; наличие иллюстрации не подтверждает технические характеристики BAUF.

| Ресурс | Назначение | Подготовка |
|---|---|---|
| wireframe/assets/calculator/matte-pvc.webp | Матовый ПВХ, карточка и большой предпросмотр | ImageGen PNG → Pillow, WebP quality 82, 960×720 |
| wireframe/assets/calculator/spots.webp | Точечные светильники, карточка и предпросмотр | ImageGen PNG → Pillow, WebP quality 82, 960×720 |
| wireframe/assets/calculator/fabric.webp | Ткань, карточка и большой предпросмотр | ImageGen PNG → Pillow, WebP quality 82, 960×720 |

Промпт ПВХ:

> Use case: photorealistic-natural. Create a single architectural ceiling material illustration for a Russian stretch-ceiling configurator. Close upward view of an ordinary modern room corner, plain evenly matte white PVC stretched ceiling, smooth untextured planar surface with absolutely no reflections or gloss, simple white wall junction with narrow white insert, warm pale beige walls, soft natural daylight. Ceiling occupies 75 percent of frame, no people, text, logos, lamps or complex structures. Realistic neutral architectural product photography, horizontal 4:3 composition. This is an explanatory generated illustration, not a completed client project.

Промпт ткани:

> Use case: photorealistic-natural. Architectural product illustration for a stretch-ceiling configurator. Close upward view of a modern room corner, matte white textile stretch ceiling with very subtle fine woven fabric texture, warm pale beige walls, no glossy reflections. Same clean neutral photographic aesthetic as a white matte PVC ceiling sample, but the fine textile grain is visible in the near foreground. Ceiling occupies 75 percent, daylight, physically plausible flat tensioned ceiling, narrow wall boundary. No people, text, logos, watermarks, furniture or lamps. Horizontal 4:3. Explanatory material illustration only, not a documented client installation.

Исходные генерации остаются вне репозитория, в каталоге Codex generated_images текущего чата. В проекте используются только оптимизированные WebP, новые runtime-зависимости для изображений не добавлялись.

Промпт светильников:

> Use case: photorealistic-natural. Architectural product illustration for ceiling configurator, horizontal 4:3. Upward view of warm beige modern interior, plain matte white stretch ceiling with four small circular recessed LED spotlights, evenly spaced, white trims flush to ceiling and softly glowing lenses. All four spots visible and clearly identifiable, ceiling dominates frame with a small wall corner at lower edge. Soft daylight, realistic physically plausible ceiling installation, neutral quiet photographic style. No people, furniture, text, logos, watermarks, tracks, pendant lights or linear lighting. Explanatory generated illustration, not a photograph of a documented installation.

## Существующие материалы

`light-lines.jpg`, `magnetic-tracks.jpg`, `penthouse-chandelier.jpg`, `cornice.jpg` показывают линии, треки, люстру и нишу. Это уже имеющиеся материалы сайта; подпись не выдаёт их за подтверждённые выполненные VLICO объекты. Старый fabric-bauf.jpg не используется новым калькулятором: общее интерьерное фото заменено отдельной иллюстрацией ткани.

В `backend/static/calculator/view.js` находятся SVG-сечения обычного, теневого и парящего примыкания, открытого карниза, контурной подсветки и геометрии помещения. Это схемы принципа, а не монтажные чертежи. Не подтверждают конкретный артикул профиля. Подписи объясняют ограничения. Геометрия прямоугольника использует единый масштаб; на экстремальных пропорциях минимальные размеры сохраняют читаемость, точные значения остаются в подписях.

Все растровые элементы имеют width/height и lazy loading, на телефоне крупный предпросмотр ограничен по высоте. Неактивные шаги не создают растровые узлы. Окончательное соответствие образцам полотна и монтажным узлам должен подтвердить специалист компании; карточки не заменяют подбор оборудования на замере.
