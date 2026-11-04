# Освещение в одной комнате

Доработка 04.11.2026: пользователь попросил убрать клиентские фото из шага освещения и показать разные системы в одинаковой комнате. Созданы пять новых изображений: точечные светильники, световые линии, магнитные треки, подвес, контурный LED. Геометрия, мебель, ракурс и вечерний свет из окна сохранены; меняется только система искусственного света и её действие на интерьер. Клиентские фото не использованы как reference: основа — ранее сгенерированная комната `room-matte.webp`.

Все пять ответов имеют фотографии в карточках, переключаемом предпросмотре и увеличении. «Без нового освещения» и «Пока не определился» остаются текстовыми. При выборе нескольких систем предпросмотр показывает последнюю выбранную; отдельные кнопки позволяют рассмотреть выбранные системы без изменения галочек и количеств. Подпись объясняет, что показан один вид света, а не автоматически совмещённый световой проект. Схемы света удалены. Старый `calculator/spots.webp` удалён как неиспользуемый. Исходные клиентские фотографии остаются в проекте для других разделов, но шаг освещения на них больше не ссылается.

Ни количество светильников на картинке, ни их длины не назначаются в ответах автоматически. Пользователь вводит свои параметры. Расчёт, ставки, неизвестные количества, исключения оборудования и отсутствие двойного начисления парящего LED не менялись. Изображения помечены как ИИ-иллюстрации, не являются реальными выполненными объектами, комплектом конкретного оборудования или светотехническим расчётом.

## Ресурсы

Встроенный ImageGen: master с шестью точечными светильниками, затем четыре редактирования одного master. Все результаты визуально просмотрены. Только ресайз и WebP-экспорт выполнены Pillow. В `wireframe/assets/calculator/` — `light-{spots,lines,tracks,pendant,contour}.webp` (1440×1080, quality 86) и `light-*-small.webp` (480×360, quality 82). Есть srcset/sizes, lazy loading, стабильная геометрия 4:3. Новых зависимостей нет.

| Вариант | Исходный PNG в generated_images текущего чата |
|---|---|
| Spots | exec-29648275-a389-48ad-bfe0-c0d41d8abcfe.png |
| Lines | exec-0045a96b-fa00-4946-b7e0-7e65846d09fa.png |
| Tracks | exec-1b1db9cc-00ea-4140-8f5d-f006715461d7.png |
| Pendant | exec-0c82e873-45ed-4ca0-98d4-2ba751ced73a.png |
| Contour | exec-204b8969-e7a2-46d9-acaf-fdbafe8c9c41.png |

Промпт master (reference: room-matte.webp):

> Precise lighting-only edit of supplied generated living-room reference to create a MASTER for lighting comparisons. Preserve EXACT room geometry, camera, crop, beige sofa, armchair, oak coffee table, vase branches, books, rug, walnut wall and framed artwork, window and curtains. Keep the plain MATTE WHITE stretch ceiling and its edges. Change time of day to soft blue-hour dusk: window and outside still visible, subdued ambient daylight, enough light to see furniture and true warm-neutral colors. Add ONLY recessed circular spotlights: six small white flush circular downlights arranged in two neat rows of three across the ceiling, switched ON with a warm-white soft glow and physically plausible subtle pools of light. Remove the old three unlit spots. No linear lights, no tracks, no pendant, no perimeter LED or coving. Ceiling remains flat, no decorative beams. Architectural photorealistic interior, calm restrained exposure, not dark or dramatic. Lighting hardware visibly understandable at thumbnail size. Horizontal 4:3 full image. No text, watermark, branding or people. This is a generated explanatory comparison, not a documented client interior. This exact room and dusk ambient exposure will be locked for four later lighting-system edits.

Общий промпт редактирования, master передан как referenced_image_paths:

> Precise LIGHTING-SYSTEM-ONLY edit of the attached MASTER living-room photograph. HARD LOCK identical camera, horizontal 4:3 crop, room geometry, walls, matte ceiling, furniture, window, sheer curtains, blue-hour exterior, floor, plant branches, vase, books and artwork. Keep SAME soft dusk ambient and natural exposure; no restyling, no changes of materials. REMOVE ALL SIX EXISTING CIRCULAR SPOTLIGHTS and their old light pools; smoothly restore the ceiling at those locations. Replace their lighting with the following single system: [вариант ниже] Show physically plausible illumination from the new system, keeping furniture visible. All other lighting systems must be absent, so this single option is unambiguous at thumbnail size. Photorealistic architectural photo, no text, labels, logos, watermarks or people. Generated explanatory visualization, not a documented customer project.

- Lines: ONLY TWO LONG PARALLEL RECESSED LIGHT LINES integrated flush into the matte white ceiling, running from foreground toward the back wall in perspective. Continuous slim white diffusers, about 30 mm wide in real life, softly glowing warm white. Clearly recognizable unbroken linear lighting, not hanging bars or black tracks. No circular spotlights at all.
- Tracks: ONLY TWO SLIM BLACK MAGNETIC TRACK RAILS recessed into the ceiling, running parallel from foreground toward back wall in perspective. In each track, three small clearly visible black cylindrical adjustable spot modules are attached and directed downward, warm-white illuminated beams. Rails remain dark and visible; this must visually differ from continuous glowing light lines. No ordinary recessed ceiling spotlights, no pendant, no perimeter LED.
- Pendant: ONLY ONE DECORATIVE PENDANT centered above the coffee table: a simple elegant broad shallow warm-white glowing opal dome suspended on a thin dark cable from a small ceiling canopy. Pendant hangs naturally at a plausible height without colliding with the vase or furniture. A single intentional focal lighting fixture, no other ceiling spotlights, rails, glowing lines or perimeter light.
- Contour: ONLY CONCEALED PERIMETER LED LIGHTING around the entire visible ceiling edge. Continuous warm-white light from a narrow hidden ceiling-wall gap creates soft evenly lit upper walls and a subtle floating ceiling effect. No visible LED dots or exposed tape, no large cornice or dropped soffit. Remove every circular spotlight and its pools of light. No central lights, tracks, pendants or lines within the ceiling plane.

Размеры, количество и цвет света в промптах описывают иллюстрации, не технические обязательства по проекту.

## Проверка

Пройдены Docker build/up, JS syntax check, тест клиентской модели и 36 серверных тестов калькулятора/заявок. `scripts/test-lighting-comparison.js` проверяет пять новых изображений без ссылок на клиентские фото, отсутствие SVG, последний выбранный предпросмотр, увеличение, множественный выбор, переключение предпросмотра без изменения параметров, ввод количества и клик после потери фокуса, возврат назад, исключающий ответ «Без нового освещения», ширины 1440/1024/768/390/320 без overflow. Снимки: screenshots/lights-desktop.png и lights-mobile.png.

При визуальном проходе найден потерянный клик после ввода количества: дублирующий обработчик change перерисовывал панель на blur и удалял нажатую кнопку до click. Числовые поля теперь обрабатываются только через input; change отвечает за radio/checkbox. Сценарий закреплён браузерной проверкой.


После возобновления 05.11.2026 повторно пройдены сценарий освещения (включая клик после ввода количества) и 36 серверных тестов. Docker был остановлен; выполнен один штатный запуск с проверкой docker info, затем восстановлены существующие контейнеры без изменения данных.
