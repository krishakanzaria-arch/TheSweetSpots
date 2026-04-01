from django.urls import path
from dashboard.views import product_add
from dashboard import views
from .import views
from .views import add_to_wishlist,checkout,order_success, my_account,login_view,logout_view,verify_otp,forgot_password,reset_password, page, remove_from_cart, remove_from_wishlist, shop_grid,index, update_cart_qty, wishlist_view,add_to_cart,view_cart


urlpatterns = [
    path('', page, {'page_name': 'index'}, name='home'),
    path('shop-grid/', shop_grid, name='shop_grid'),
    path('index/', index, name='index'),
    path('menu/',views.menu, name='menu'),
    path('add-to-cart/<int:product_id>/', add_to_cart, name='add_to_cart'),
    path('cart/', view_cart, name='cart'),
    path('cart/update/<int:product_id>/<str:action>/', update_cart_qty, name='update_cart_qty'),
    path('cart/remove/<int:product_id>/', remove_from_cart, name='remove_from_cart'),
    path('wishlist/add/<int:product_id>/',add_to_wishlist, name='add_to_wishlist'),
    path('wishlist/remove/<int:product_id>/', remove_from_wishlist, name='remove_from_wishlist'),
    path('wishlist/', wishlist_view, name='wishlist'),
    path('my-account/',my_account, name='my_account'),
    path('forgot-password/', forgot_password, name='forgot_password'),
    path('verify-otp/', verify_otp, name='verify_otp'),
    path('reset-password/', reset_password, name='reset_password'),
    path('login/',login_view, name='login'),
    path('logout/',logout_view, name='logout'),
    path('checkout/', checkout, name='checkout'),
    path('order-success/<int:order_id>/', views.order_success, name='order_success'),
    path('my-orders/', views.my_orders, name='my_orders'),
    path('my-orders/<int:order_id>/', views.my_order_detail, name='my_order_detail'),
    path('cancel-order/<int:order_id>/', views.cancel_order, name='cancel_order'),
    path('profile/', views.user_profile, name='user_profile'),
    path('pay/<int:order_id>/', views.start_online_payment, name="start_online_payment"),
    path('pay/link/<int:order_id>/', views.create_payment_link, name='payment_link'),
    path('paysuc/',views.payment_success,name="payment_success"),
    path('payment-cancel/', views.payment_cancel, name='payment_cancel'),
    path('add-review/<int:product_id>/',views.add_review,name='add_review'),
    path('order/<int:order_id>/return/', views.start_return, name='start_return'),
    path('invoice/<int:order_id>/', views.download_invoice, name='download_invoice'),
    path('product-details/<int:pk>/', views.product_details, name='product_details'),
    path('customize-cake/', views.customize_cake, name='customize_cake'),
    path('custom-checkout/', views.custom_checkout, name='custom_checkout'),
    path('start-custom-online-payment/<int:order_id>/', views.start_custom_online_payment, name='start_custom_online_payment'),
    path('<str:page_name>/', page, name='page'),
]