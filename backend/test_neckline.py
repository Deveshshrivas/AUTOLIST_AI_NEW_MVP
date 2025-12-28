from app.workers.normalizer import normalize_product, extract_neckline

product = {
    'title': "Men's Cotton Kurta - Blue",
    'body_html': '<p>Premium 100% cotton kurta with mandarin collar. Full sleeves. Perfect for ethnic occasions.</p>',
    'vendor': 'Fabindia',
}

normalized = normalize_product(product)
print('Extracted neckline:', normalized.get('extracted_neckline'))

all_text = product.get('title', '') + ' ' + product.get('body_html', '')
print('Testing direct on combined text:', extract_neckline(all_text))
print('\nAll text:', all_text)
