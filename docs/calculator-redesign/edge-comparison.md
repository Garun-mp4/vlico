# Реалистичные изображения примыкания

Доработка 04.11.2026: по просьбе пользователя SVG-сечения на шаге 4 заменены реалистичными изображениями готового потолка. Для сравнения выбран близкий ракурс одного угла комнаты: в общей интерьерной фотографии узкий зазор был бы слишком мелким. Три версии сохраняют ракурс, стены, освещение и раму картины:

- Классическое примыкание: закрытый стык с тонкой белой вставкой.
- Теневое: непрерывный тёмный зазор без подсветки.
- Парящее: скрытый световой контур и мягкий свет вдоль стены.

Ответ «Пока не знаю» текстовый. Исправлен дефект общего выбора медиа: ранее любой `edge:*`, включая unknown, превращался в схему теневого профиля. Теперь ресурс назначается только конкретным известным вариантам; аналогичные неопределённые ответы карнизов также не получают случайную конструктивную схему.

Изображения работают в карточках, переключаемом предпросмотре и общем native dialog увеличения. Dialog переиспользуется и для материалов, закрывается кнопкой/Escape и возвращает фокус. До выбора показан подписанный пример классического стыка без автоматического выбора ответа. При «Пока не знаю» вместо изображения конкретного профиля показано предложение помочь с подбором. Иллюстрации помечены как созданные ИИ и не выдаются за выполненный объект или точный монтажный чертёж конкретного профиля. Тарифы, коды вариантов, формулы и заявки не изменены.

## Ресурсы

Встроенный ImageGen создал master классического стыка, затем два независимых редактирования master. Каждый результат визуально проверен. В `wireframe/assets/calculator/` находятся `edge-classic.webp`, `edge-shadow.webp`, `edge-floating.webp` (1440×1080) и соответствующие `-small.webp` (480×360). Экспорт Pillow: только resize/WebP, quality 86/82. Используются srcset/sizes, lazy loading и фиксированное соотношение сторон 4:3. Новых зависимостей нет.

Исходные генерации в каталоге Codex generated_images текущего чата:

| Вариант | PNG |
|---|---|
| Classic | exec-ec3edc2f-294f-4967-bae7-e7deacd3e0c4.png |
| Shadow | exec-8a2d4b6a-c0f4-4c20-963d-9c8088b0b7c6.png |
| Floating | exec-5a94c656-467f-4d4c-9d85-c33f0279f389.png |

Промпт master:

> Use case: photorealistic-natural. MASTER reference photograph for comparing three REALISTIC stretch-ceiling wall junctions. One horizontal 4:3 architectural interior DETAIL PHOTO, NOT a diagram, not a cutaway. Camera looking obliquely upward at the upper inside corner of a modern living room. White matte stretched ceiling occupies upper 45 percent, warm pale beige plaster walls lower 55 percent. The back-wall ceiling junction runs horizontally from left edge toward the upper right interior corner, then continues diagonally toward the right foreground, so the entire visible L-shaped junction is clearly legible. Show natural fine plaster and ceiling surface, soft neutral daylight coming from left. Lower right just a small top corner of a walnut picture frame for human-scale context, otherwise uncluttered. CLASSIC installation: thin WHITE flexible masking insert tightly closes the ceiling-wall mounting joint, a clean narrow white strip at junction, no dark recessed slot, no illumination, NO crown molding, no ornate cornice, no large dropped soffit. The visible joint must look like a standard white PVC stretch ceiling finished with a white insert. Professional restrained interiors photography, realistic exposure, no people, text, captions, logos, watermarks, profile cross sections or construction drawings. A generated explanatory visualization, not a photo of an actual client's project. Lock exact camera, geometry, wall texture, picture frame and lighting for later shadow-gap and floating-light edits.

Общий промпт редактирования (master передан как referenced_image_paths):

> Precise architectural detail photo edit. Preserve EXACT camera, framing, wall and ceiling plane geometry, corner location, beige wall plaster texture, daylight and wooden picture frame of supplied MASTER. Change ONLY the thin L-shaped junction between ceiling and walls. [Вариант ниже] Same horizontal 4:3 output. Keep realistic thin architectural proportions. No diagram, cross-section, labels, text, logos or people. This is a generated explanatory illustration of a finished interior.

- Shadow: SHADOW GAP stretch-ceiling junction. Replace the thin white masking insert along BOTH wall-ceiling boundaries with a clean narrow deep-black recessed shadow slot, about 8 mm wide in reality. The slot must be clearly visible as a consistent crisp dark line along the horizontal back-wall edge AND the diagonal right-wall edge. No LED lighting, no glow, no coving, no crown molding. Ceiling otherwise unchanged.
- Floating: FLOATING LED stretch-ceiling junction. Replace the white insert along BOTH wall-ceiling boundaries with a small recessed lighting gap. A continuous concealed warm-white 3000K LED inside this gap creates an unmistakable even luminous perimeter line and a gentle warm wash down the upper beige walls. Light source is hidden inside the narrow profile, no visible dots, bulbs, fixtures or exposed tape. Make light visible in daylight without darkening whole room. The white ceiling appears slightly detached from walls due to this luminous separation. NO large dropped soffit or crown molding.

Размер зазора и температура света в промптах направляют иллюстрацию и не являются характеристиками предлагаемой комплектации.

## Проверка

Docker build/up, JS syntax check, тест клиентской модели и 36 Django-тестов калькулятора/заявок прошли. В браузере `scripts/test-edge-comparison.js` проверяет три разных загружаемых изображения, отсутствие SVG и картинки у unknown, переключение, увеличение, Escape/возврат фокуса, сохранение выбора и ширины 1440/1024/768/390/320 без overflow. Повторно пройден `scripts/test-material-comparison.js`, подтверждена работа общего dialog на предыдущем шаге. Необработанных исключений JS нет. Снимки: screenshots/edges-desktop.png и edges-mobile.png. Реальные образцы профилей и комплектацию по-прежнему согласуют после замера.
