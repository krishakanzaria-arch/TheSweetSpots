from django.urls import path
from .views import page, logout_view, product_add, product_list,product_edit,product_delete,orders_list,order_detail
from dashboard import views

app_name = 'dashboard'

urlpatterns = [
    path('', page, {'page_name': 'index'}, name='home'),
    path('logout/', logout_view, name='logout'),
    path('product-add/', product_add, name='product_add'),
    path('product-edit/<int:product_id>/', product_edit, name='product_edit'),
    path('product-delete/<int:product_id>/', product_delete, name='product_delete'),
    path('product-list/',product_list, name='product_list'),
    path('orders-list/', orders_list, name='orders_list'),
    path('order-detail/<int:order_id>/', order_detail, name='order_detail'),
    path('orders/<int:order_id>/update-status/', views.update_order_status, name='update_order_status'),
    path('payment/update-status/<int:payment_id>/', views.update_payment_status, name='update_payment_status'),
    path('customer-list/',views.customers_list, name='customers_list'),
    path('index/',views.dashboard_list,name='dashboard_list'),
    path('pages-review/',views.review_list,name='review_list'),
    path('return-requests/',views.return_requests,name='return_requests'),
    path('approve_return/<int:return_id>/', views.approve_return, name='approve_return'),
    path('reject_return/<int:return_id>/', views.reject_return, name='reject_return'),
    path('customers/delete/<int:user_id>/', views.delete_customer, name='delete_customer'),
    path('add-category-subcategory/',views.add_category_and_subcategory,name='add_category_subcategory'),
    path('coupons-add/', views.coupon_add, name='coupon_add'),
    path('coupons-list/', views.coupon_list, name='coupon_list'),
    path('sales-report-pdf/', views.sales_report_pdf, name='sales_report_pdf'),
    path('customer-report-pdf/', views.customer_report_pdf, name='customer_report_pdf'),
    path('revenue-summary-pdf/', views.revenue_summary_pdf, name='revenue_summary_pdf'),
    path('stock-report/', views.stock_report, name='stock_report'),
    path('add-batch/', views.add_batch, name='add_batch'),
    path('<str:page_name>/', page, name='page'),
]