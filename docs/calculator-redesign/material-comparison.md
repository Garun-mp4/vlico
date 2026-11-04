# Сравнение материалов в одной комнате

Доработка 04.11.2026 по замечанию пользователя: крупные планы двух белых углов не объясняли разницу. Вместо них показана одна гостиная в четырёх версиях поверхности потолка: матовый ПВХ, сатиновый ПВХ, глянцевый ПВХ, ткань. Пятая опция — помощь с выбором. Обстановка, ракурс и свет сохранены; глянец отличается отражениями окна и мебели, сатин — мягким отсветом, ткань — видимым переплетением. Эти изображения иллюстрируют характер поверхностей, не являются снимками выполненного объекта или сертифицированными образцами производителя.

## Интерфейс и данные

Карточки 2×2 показывают полный кадр 4:3. Слева есть подписанный предпросмотр ещё до выбора, без скрытого назначения материала. Нажатие «Рассмотреть крупнее» открывает native dialog с полным изображением; закрытие кнопкой и Escape, возврат фокуса. Предпросмотр переключается вместе с ответом. На телефоне карточки идут первыми, крупная картинка не отодвигает вопрос.

Код `pvc` сохранён для совместимости прежних черновиков и означает матовый ПВХ. Добавлены публичные значения `pvc_satin` и `pvc_gloss`. В сохранённом расчёте отдельно записаны `material` (pvc/fabric), `texture` (matte/satin/gloss/textile) и `surface` (исходный вариант ответа). Сводка и заявка сохраняют точное название выбранной поверхности.

На сатин и глянец нет утверждённых отдельных ставок. Они добавлены как пожелания клиента с подписью «Доступность и стоимость уточним». Результат — индивидуальный расчёт с объяснением; ставка матового ПВХ не выдаётся за цену новой фактуры. Матовый ПВХ и ткань используют прежние серверные правила. Источник ставок и кабинет не менялись.

## Ресурсы и происхождение

Встроенный ImageGen: сначала новый master-кадр матового потолка, затем три независимых редактирования этого master с сохранением комнаты. Результаты визуально просмотрены. Pillow использован только для ресайза и WebP-экспорта. Полные кадры 1440×1080, карточки 480×360, quality 86/82. `srcset/sizes`, lazy loading и заданная геометрия предотвращают лишний вес и скачки. Старые неиспользуемые `matte-pvc.webp` и `fabric.webp` удалены.

| Файлы в wireframe/assets/calculator/ | Исходная генерация |
|---|---|
| room-matte.webp, room-matte-small.webp | exec-103edcbf-7bd8-4459-ac0c-d970ad8403c6.png |
| room-satin.webp, room-satin-small.webp | exec-d16f7011-deb8-4131-af1c-0ac5668b4b02.png |
| room-gloss.webp, room-gloss-small.webp | exec-fe54cf4b-0456-4495-8a07-858e5ccd0403.png |
| room-fabric.webp, room-fabric-small.webp | exec-20c8122c-3bb8-4e8e-a067-8c5aa6052b6a.png |

Промпт master:

> Use case: photorealistic-natural. Generate the MASTER REFERENCE image of one room for an exact same-room ceiling-material comparison on an architectural website. Single horizontal 4:3 photorealistic interior photo. Camera at seated height looking upward into an elegant restrained contemporary living room. The clearly visible ceiling fills the upper 55 percent of the frame; the lower 45 percent shows the tops of a warm beige low sofa on left, one dark walnut sculptural armchair at right, a low oak coffee table, beige plaster walls. At left rear is a large floor-to-ceiling window with a sheer white curtain through which soft daylight enters; at right rear a dark walnut wall with a single simple framed abstract print. Clean ordinary rectangular room, level white stretched ceiling with MATTE PVC finish, perfectly smooth evenly white, diffuse light, absolutely NO reflections of the window or furnishings in the ceiling. Three small white recessed spotlights in a straight line near back wall, switched off. No hanging lamps, no perimeter LED, no ceiling beams, no elaborate ceiling shapes. The composition must clearly show both ceiling and enough furniture/window that subsequent satin/gloss variants can reflect those exact elements. Warm neutral cream palette, architectural editorial photography, natural exposure with white detail retained. No people, logos, lettering or watermarks. This is an explanatory generated illustration, not a photograph of a documented client project. The whole room, camera, crop, furniture and lighting will be locked for subsequent material edits.

Общий промпт редактирования (master передан через referenced_image_paths):

> Precise material-only edit of attached MASTER room photograph. HARD LOCK: keep identical camera, pixel framing, geometry, wall-ceiling junctions, exact three recessed spots and their positions, every furnishing, vase, plant, books, sofa, chair, window, curtain, artwork, oak floor and lighting. DO NOT redesign the room or change white balance or exposure below the ceiling. Change ONLY the surface finish of the upper ceiling plane. Variant: [описание ниже] Output one horizontal 4:3 image matching original dimensions and crop. No text, labels, logos, watermarks, people. Image is a generated illustrative comparison, not a completed client object.

- Satin: SATIN WHITE PVC: silky pearlescent surface, gentle wide soft window light sheen on ceiling left, blurred low-contrast light reflection only, no sharp furniture mirror. Visibly a little more luminous and subtly reflective than master matte, physically plausible satin tensioned membrane.
- Gloss: HIGH-GLOSS WHITE PVC: a smooth white mirror-like stretched membrane, clear visible physically plausible upside-down reflections of the LEFT WINDOW and sheer curtains, and ghosted beige sofa, vase greenery and walnut wall elements. Reflectivity should be unmistakable at thumbnail size but ceiling stays white/light, not dark gray, no water appearance, no ripples, no liquid. Reflections are seen ONLY within the exact existing ceiling plane. Do not add furniture or lights.
- Fabric: WHITE TEXTILE STRETCH CEILING: completely matte with fine visible woven textile grain at the near ceiling foreground. Slightly warmer soft diffuse whites than master matte PVC. Fine textile weave subtly legible in large preview, without giant fabric threads or cracks. No reflections, no gloss, no seams, no pleats, no hanging fabric.

## Проверки

82 Django-теста прошли, включая разделение материала/фактуры, отсутствие выдуманного тарифа, запись выбранной фактуры в настоящую тестовую заявку и сохранение прежних контрольных сумм. Клиентская модель прошла прежние проверки. `scripts/test-material-comparison.js` через playwright-cli проверяет четыре изображения, переключение предпросмотра, декодирование файлов, native dialog/Escape, возврат и reload, отсутствие overflow на 1440/1024/768/390/320. Снимки: screenshots/materials-desktop.png и materials-mobile.png. Изображения помечены как ИИ; точное соответствие образцам определяется на встрече со специалистом.
