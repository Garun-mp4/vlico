# Шторы: сравнение в одной комнате

Доработка 05.11.2026: по просьбе пользователя схемы и исходная фотография заменены четырьмя реалистичными изображениями одного окна в одной комнате. Показаны видимый потолочный карниз, скрытая ниша, настенный карниз и окно без карниза/штор. Пятый ответ «Пока не определился» текстовый. Ракурс выбран ближе к окну, чтобы было видно место крепления и начало штор; сохранены окно, стены, мебель, освещение и цвет тканей.

Изображения используются в карточках, переключаемом предпросмотре и общем увеличении с Escape/возвратом фокуса. До ответа показывается подписанный пример потолочного карниза без автоматического выбора. У неопределённого ответа нет изображения конкретной конструкции. У варианта «Карниз не нужен» действительно показано окно без карниза и штор. SVG теперь используется только для геометрии помещения. Из калькулятора полностью исключён cornice.jpg; сам файл клиента сохранён для других материалов проекта.

Названия/коды вариантов и ставки не изменены. Длина запрашивается только для потолочного и скрытого карниза; при выборе настенного/отсутствующего карниза не учитывается. Изображения не задают длину или техническую комплектацию автоматически. Это ИИ-иллюстрации внешнего вида, не подтверждённые выполненные объекты или монтажные чертежи конкретных профилей.

## Ресурсы и промпты

Встроенный ImageGen: новый master с потолочным карнизом, затем три редактирования одного master. Каждый результат визуально проверен. Pillow использован только для ресайза и WebP. В `wireframe/assets/calculator/` находятся `curtain-{ceiling,hidden,wall,none}.webp` (1440×1080, quality 86) и варианты `-small.webp` (480×360, quality 82). Есть srcset/sizes, lazy loading, стабильное соотношение 4:3. Новых зависимостей нет.

| Вариант | Исходная генерация в generated_images текущего чата |
|---|---|
| Ceiling | exec-5ff40fd9-35e5-47c6-9bae-776dd8e9e924.png |
| Hidden | exec-18bff4bf-189e-4c48-b0bf-945eb7233eaa.png |
| Wall | exec-420696f0-0538-4335-ae3e-aa297a9f3a05.png |
| None | exec-90496648-c583-45fc-99ee-b79360ffeb97.png |

Промпт master:

> Use case: photorealistic-natural. Create a MASTER image for comparing curtain installation options in exactly the same room. Horizontal 4:3 architectural interior photograph, warm minimalist contemporary living room. Camera at eye level looking slightly upward and obliquely toward one large rectangular window occupying central 65 percent of frame. The window has a visible 25 cm band of beige plaster wall between the top of the window frame and the flat matte white stretch ceiling; enough headroom that a wall-mounted rod can be illustrated in later edits. Show ceiling upper 20-25 percent and most of full-height curtains to floor. Soft daylight, trees outside. Warm pale beige plaster walls, light oak floor, a small top corner of a beige armchair at lower right. Curtains: sheer off-white inner panels and warm oatmeal solid side drapes, open around the window. PRIMARY SUBJECT: a VISIBLE SLIM WHITE CEILING-MOUNTED CURTAIN TRACK fixed directly UNDER the ceiling plane along the window wall. Its narrow white rail profile must be clearly seen in front of wall/above curtain headings; curtain hooks/runners attach to underside. Ceiling is flush without hidden recess or niche; the rail is not concealed by a valance, crown molding or soffit. No wall-mounted rod, no LED lighting. Natural convincing folds, realistic architectural construction, physically plausible proportions. Photo should make the visible ceiling rail understandable at thumbnail size. No people, text, labels, logos, watermark or diagrams. Generated explanatory visualization, not documented customer work. Exact window, room, camera, furniture and lighting will be locked for later hidden-track, wall-rod and no-curtains variants.

Общий промпт редактирования (master передан через referenced_image_paths):

> Precise curtain-installation-only edit of attached MASTER interior photograph. HARD LOCK same camera, horizontal 4:3 crop, room geometry, window position and frame shape, beige plaster walls, white ceiling, oak floor, beige armchair at right, outdoor trees, daylight, white balance and exposure. Change ONLY the curtain mounting treatment as follows: [вариант ниже] Photorealistic finished residential interior, normal realistic construction and fabric folds. No text, labels, arrows, diagrams, logos, watermarks or people. A generated explanatory illustration, not a photograph of documented client work.

- Hidden: HIDDEN CEILING CURTAIN NICHE: remove the visible white rail and ALL visible hooks/runners from the image. The same sheer and oatmeal drapes emerge directly from a narrow clean recessed slot just behind the finished stretch-ceiling edge along this window wall. A subtle dark recess at top makes the origin readable, while rail hardware is completely concealed above/inside the niche. Show a clean minimalist ceiling edge, NOT a large decorative cornice, pelmet, bulky beam or LED strip. Keep curtain lengths to floor and open arrangement. The essential difference: no surface-mounted rail can be seen; drapes appear to fall from a ceiling recess.
- Wall: WALL-MOUNTED CURTAIN ROD: completely remove the white ceiling track, its hooks, and all ceiling attachments, leaving flat plain ceiling. Add a slim dark bronze horizontal curtain rod on three visible short brackets fixed into the WALL above the window, distinctly BELOW the ceiling with visible beige wall between rod and ceiling. Curtain rod has small plain end caps and rings. Hang the same oatmeal drapes and sheer off-white curtains from a practical double wall-mounted rod arrangement; top of curtains follows wall-rod height, curtains still reach floor. The wall fixing must be visually unmistakable; no ceiling rail or niche.
- None: NO CURTAINS OR CORNICE: remove ALL solid oatmeal drapes, ALL white sheer curtains, ALL rods, ceiling rails, hooks, brackets and other window-covering hardware. Reveal the same uncovered white-framed window and beige walls around it. Restore flat plain matte white ceiling with an ordinary wall junction, no niche, no LED, no holes, no marks. Keep the original precise window frame, outside trees, floor, chair and daylight. Clean ordinary room with a bare window, so this option unambiguously means no curtain installation.

Числа в промптах направляют иллюстрации и не являются обещанными размерами комплектации.

## Проверка

Браузерный сценарий `scripts/test-curtain-comparison.js` проверяет четыре загружаемых изображения без исходного фото/SVG, увеличение всех вариантов, Escape/возврат фокуса, условное поле длины, сохранение параметров при смене вариантов и возврате, текстовый неизвестный ответ, ширины 1440/1024/768/390/320 без overflow. Снимки: screenshots/curtains-desktop.png и curtains-mobile.png. Пройдены 36 серверных тестов калькулятора/заявок, Django check, JS syntax check и тест клиентской модели. Полный браузерный сценарий сохранил контрольную сумму 50900 ₽, ответы и корректную работу формы; необработанных исключений JS и horizontal overflow не обнаружено. Docker build/up завершились успешно.
