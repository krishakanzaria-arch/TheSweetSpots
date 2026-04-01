def wishlist_count(request):
    wishlist = request.session.get('wishlist', [])
    return {'wishlist_count': len(wishlist)}