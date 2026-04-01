from datetime import date

from django.shortcuts import render, redirect,get_object_or_404
from django.contrib.auth import logout, authenticate, login
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.http import HttpResponse, HttpResponseForbidden
import os
from django.utils.dateparse import parse_date
from django.conf import settings
import matplotlib.pyplot as plt
import calendar
from io import BytesIO
from django.db.models.functions import ExtractMonth
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import pagesizes
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet
from django.utils.dateparse import parse_date
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.db.models import Sum, Q
from django.db.models.functions import TruncDate
import json
from django.contrib.auth import get_user_model
from django.contrib import messages
from bakery.models import Product,ProductCategory,ProductSubCategory,Order,UserProfile,Payment,ProductReview,OrderReturn,Coupon, ProductBatch
from .forms import ProductCategoryForm, ProductSubCategoryForm, ProductBatchForm


# pages allowed without authentication (e.g. signin/signup/error pages)
PUBLIC_PAGES = {'auth-signin', 'auth-signup', 'error-404', 'auth-password-reset'}

def add_batch(request):

    if request.method == "POST":
        form = ProductBatchForm(request.POST)
        if form.is_valid():

            expiry = form.cleaned_data['expiry_date']

            # ❌ Prevent adding already expired batch
            if expiry < timezone.now().date():
                messages.error(request, "Cannot add expired batch.")
                return redirect('dashboard:add_batch')

            form.save()
            messages.success(request, "Batch added successfully.")
            return redirect('dashboard:add_batch')

    else:
        form = ProductBatchForm()

    return render(request, 'dashboard/admin/add-batch.html', {'form': form})

def remove_expired_batches():
    expired_batches=ProductBatch.objects.filter(expiry_date__lt=date.today())
    for batch in expired_batches:
        product=batch.product
        product.stock -= batch.quantity
        if product.stock < 0:
            product.stock = 0
        product.save()
        batch.delete()

def dashboard_home(request):

    remove_expired_batches()  # auto cleanup

    return render(request, "dashboard/home.html")

def stock_report(request):

    products = Product.objects.all()

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="stock_report.pdf"'

    doc = SimpleDocTemplate(response, pagesize=pagesizes.A4)
    elements = []
    styles = getSampleStyleSheet()

    # ===== Logo =====
    logo_path = os.path.join(settings.BASE_DIR, 'static/images/favicon.png')
    if os.path.exists(logo_path):
        logo = Image(logo_path, width=1.5*inch, height=1.5*inch)
        elements.append(logo)


    elements.append(Paragraph("<b>TheSweetSpots</b>", styles['Title']))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph("Inventory / Stock Report", styles['Normal']))
    elements.append(Spacer(1, 20))

    data = [['Product', 'Category', 'Stock', 'Status']]

    for p in products:
        if p.stock == 0:
            status = "Out of Stock"
        elif p.stock <= 5:
            status = "Low Stock"
        else:
            status = "In Stock"

        data.append([
            p.product_name,
            p.product_category.category_name,
            p.stock,
            status
        ])

    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.pink),
        ('GRID', (0,0), (-1,-1), 1, colors.grey),
    ]))

    elements.append(table)
    doc.build(elements)

    return response

def revenue_summary_pdf(request):

    from_date = parse_date(request.GET.get('from_date'))
    to_date = parse_date(request.GET.get('to_date'))

    orders = Order.objects.filter(
        order_date__range=[from_date, to_date]
    )

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="revenue_summary.pdf"'

    doc = SimpleDocTemplate(response, pagesize=pagesizes.A4)
    elements = []
    styles = getSampleStyleSheet()

    # ===== Logo =====
    logo_path = os.path.join(settings.BASE_DIR, 'static/images/favicon.png')
    if os.path.exists(logo_path):
        logo = Image(logo_path, width=1.5*inch, height=1.5*inch)
        elements.append(logo)

    # ===== Header =====
    elements.append(Paragraph("<b>TheSweetSpots</b>", styles['Title']))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph(
        f"Revenue Summary from {from_date} to {to_date}",
        styles['Normal']
    ))
    elements.append(Spacer(1, 20))

    # ===== Calculations =====
    total_orders = orders.count()
    total_revenue = sum(o.total_amount for o in orders)
    total_gst = sum(o.gst_amount for o in orders)
    total_delivery = sum(o.delivery_charge for o in orders)
    total_discount = sum(
        o.coupon.discount_amount if o.coupon else 0
        for o in orders
    )

    net_revenue = total_revenue - total_discount

    data = [
        ['Total Orders', total_orders],
        ['Total Revenue', f'₹{total_revenue}'],
        ['Total GST Collected', f'₹{total_gst}'],
        ['Total Delivery Charges', f'₹{total_delivery}'],
        ['Total Discount Given', f'₹{total_discount}'],
        ['Net Revenue', f'₹{net_revenue}'],
    ]

    table = Table(data, colWidths=[250, 200])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.pink),
        ('GRID', (0,0), (-1,-1), 1, colors.grey),
    ]))

    elements.append(table)

    doc.build(elements)
    return response

def customer_report_pdf(request):

    from_date = parse_date(request.GET.get('from_date'))
    to_date = parse_date(request.GET.get('to_date'))

    orders = Order.objects.filter(
        order_date__range=[from_date, to_date]
    )

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="customer_report.pdf"'

    doc = SimpleDocTemplate(response, pagesize=pagesizes.A4)
    elements = []
    styles = getSampleStyleSheet()

    # ===== Logo =====
    logo_path = os.path.join(settings.BASE_DIR, 'static/images/favicon.png')
    if os.path.exists(logo_path):
        logo = Image(logo_path, width=1.5*inch, height=1.5*inch)
        elements.append(logo)

    elements.append(Paragraph("<b>TheSweetSpots</b>", styles['Title']))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph(
        f"Customer Report from {from_date} to {to_date}",
        styles['Normal']
    ))
    elements.append(Spacer(1, 20))

    # Group by customer
    customers = {}

    for order in orders:
        user = order.user
        if user not in customers:
            customers[user] = {
                'orders': 0,
                'spent': 0
            }

        customers[user]['orders'] += 1
        customers[user]['spent'] += order.total_amount

    data = [['Name', 'Email', 'Mobile', 'Total Orders', 'Total Spent']]

    for user, info in customers.items():
        data.append([
            f"{user.first_name} {user.last_name}",
            user.user.email,
            user.mobile_no,
            info['orders'],
            f"₹{info['spent']}"
        ])

    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.pink),
        ('GRID', (0,0), (-1,-1), 1, colors.grey),
    ]))

    elements.append(table)

    doc.build(elements)
    return response

def sales_report_pdf(request):

    from_date = parse_date(request.GET.get('from_date'))
    to_date = parse_date(request.GET.get('to_date'))

    orders = Order.objects.filter(
        order_date__range=[from_date, to_date]
    )

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="sales_report.pdf"'

    doc = SimpleDocTemplate(response, pagesize=pagesizes.A4)
    elements = []

    styles = getSampleStyleSheet()

    # ===== Logo =====
    logo_path = os.path.join(settings.BASE_DIR, 'static/images/favicon.png')
    if os.path.exists(logo_path):
        logo = Image(logo_path, width=1.5*inch, height=1.5*inch)
        elements.append(logo)

    # ===== Company Name =====
    elements.append(Paragraph("<b>TheSweetSpots</b>", styles['Title']))
    elements.append(Spacer(1, 12))

    elements.append(Paragraph(
        f"Sales Report from {from_date} to {to_date}",
        styles['Normal']
    ))
    elements.append(Spacer(1, 20))

    # ===== Table Data =====
    data = [
        ['Order ID', 'Customer', 'Total', 'Payment', 'Status', 'Date']
    ]

    total_sales = 0

    for order in orders:
        data.append([
            str(order.id),
            order.user.user.username,
            f"₹{order.total_amount}",
            order.payment_mode,
            order.order_status,
            order.order_date.strftime('%d-%m-%Y')
        ])
        total_sales += order.total_amount

    data.append(['', '', '', '', '', ''])
    data.append(['', '', 'Total Sales:', f"₹{total_sales}", '', ''])

    table = Table(data, repeatRows=1)

    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.pink),
        ('GRID', (0,0), (-1,-1), 1, colors.grey),
        ('ALIGN', (2,1), (3,-1), 'RIGHT'),
        ('BACKGROUND', (0,-1), (-1,-1), colors.whitesmoke)
    ]))

    elements.append(table)

    elements.append(Spacer(1, 30))
    elements.append(Paragraph(
        "Thank you for using TheSweetSpots Bakery System",
        styles['Normal']
    ))

    doc.build(elements)

    return response

def coupon_add(request):
    error = None

    if request.method == 'POST':
        code = request.POST.get('code').upper()
        discount = request.POST.get('discount')
        expiry_date = request.POST.get('expiry_date')

        if not code or not discount or not expiry_date:
            error = "All fields are required"
        elif Coupon.objects.filter(code=code).exists():
            error = "Coupon already exists"
        else:
            Coupon.objects.create(
                code=code,
                discount_amount=discount,
                expiry_date=expiry_date,
                is_active=True
            )
            return redirect('dashboard:coupon_add')

    return render(request, 'dashboard/admin/coupons-add.html', {'error': error})

def coupon_list(request):
    coupons = Coupon.objects.all()
    return render(request, 'dashboard/admin/coupons-list.html', {'coupons': coupons})

def add_category_and_subcategory(request):
    category_form = ProductCategoryForm()
    sub_category_form = ProductSubCategoryForm()

    if request.method == 'POST':

        # CATEGORY FORM SUBMIT
        if 'add_category' in request.POST:
            category_form = ProductCategoryForm(request.POST)
            if category_form.is_valid():
                category_form.save()
                return redirect('dashboard:add_category_subcategory')

        # SUB CATEGORY FORM SUBMIT
        elif 'add_sub_category' in request.POST:
            sub_category_form = ProductSubCategoryForm(request.POST)
            if sub_category_form.is_valid():
                sub_category_form.save()
                return redirect('dashboard:add_category_subcategory')

    return render(request, 'dashboard/admin/add-category-subcategory.html', {
        'category_form': category_form,
        'sub_category_form': sub_category_form
    })

def delete_customer(request, user_id):
    profile = get_object_or_404(UserProfile, user__id=user_id)

    # check if customer has orders
    if profile.orders.exists():
        messages.error(request, "Cannot delete customer. Orders exist.")
        return redirect('dashboard:customers_list')

    # delete user (profile will auto delete if OneToOne CASCADE)
    profile.user.delete()

    messages.success(request, "Customer deleted successfully.")
    return redirect('dashboard:customers_list')

def return_requests(request):
    returns = OrderReturn.objects.select_related('order').all().order_by('-return_date')

    return render(request, 'dashboard/admin/return-requests.html', {
        'returns': returns
    })

@require_POST
def approve_return(request, return_id):
    order_return = get_object_or_404(OrderReturn, id=return_id)

    order_return.status = 'APPROVED'
    order_return.save()

    order = order_return.order
    order.order_status = 'CANCELLED'
    order.payment_status = 'REFUNDED'
    order.save()

    for d in order.details.all():
        d.product.stock += d.qty
        d.product.save()

    return redirect('dashboard:return_requests')


@require_POST
def reject_return(request, return_id):
    order_return = get_object_or_404(OrderReturn, id=return_id)

    order_return.status = 'REJECTED'
    order_return.save()

    return redirect('dashboard:return_requests')

def review_list(request):
    reviews = ProductReview.objects.all().order_by('-created_at')
    return render(request, 'dashboard/admin/pages-review.html', {'reviews': reviews})

def dashboard_list(request):
    customers=UserProfile.objects.all().order_by('-id')
    total_customers=customers.count()
    total_orders=Order.objects.all().count()
    orders=Order.objects.all().order_by('-order_date')
    orders=Order.objects.prefetch_related('details').select_related('user').order_by('-id')
    total_revenue=Order.objects.filter(order_status='DELIVERED').aggregate(total=Sum('total_amount')) ['total'] or 0
    delivered = Order.objects.filter(order_status='DELIVERED').count()
    shipped = Order.objects.filter(order_status='SHIPPED').count()
    pending = Order.objects.filter(order_status='PENDING').count()
    cancelled = Order.objects.filter(order_status='CANCELLED').count()
    revenue_data = (
        Order.objects
        .filter(order_status='DELIVERED')  # only completed orders
        .annotate(date=TruncDate('order_date'))
        .values('date')
        .annotate(total=Sum('total_amount'))
        .order_by('date')
    )

    revenue_labels = [str(item['date']) for item in revenue_data]
    revenue_values = [float(item['total']) for item in revenue_data]
    customers_with_orders = Order.objects.values('user').distinct().count()
    customers_without_orders = total_customers - customers_with_orders
    return render(request, 'dashboard/admin/index.html',{'orders':orders,'customers':customers,'total_customers':total_customers,'total_orders':total_orders,'total_revenue':total_revenue,
        'delivered': delivered,
        'shipped': shipped,
        'pending': pending,
        'cancelled': cancelled,
        'revenue_labels': json.dumps(revenue_labels),
        'revenue_values': json.dumps(revenue_values),
        'customers_with_orders': customers_with_orders,
        'customers_without_orders': customers_without_orders})

def customers_list(request):
    customers=UserProfile.objects.all().order_by('-id')
    total_customers=customers.count()
    total_orders=Order.objects.all().count()
    return render(request, 'dashboard/admin/customer-list.html',{'customers':customers,'total_customers':total_customers,'total_orders':total_orders})

def update_order_status(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    if request.method == "POST":
        status = request.POST.get('order_status')
        order.order_status = status
        if status == 'DELIVERED':
            order.delivery_date=timezone.now().date()
        order.save()
    return redirect('dashboard:orders_list')

def update_payment_status(request, payment_id):
    payment = get_object_or_404(Payment, id=payment_id)
    if request.method == "POST":
        payment.status=request.POST.get('status')
        payment.save()
    return redirect('dashboard:orders_list')

def orders_list(request):
    orders=Order.objects.all().order_by('-order_date')
    total_shipped=Order.objects.filter(order_status='SHIPPED').count()
    total_delivered=Order.objects.filter(order_status='DELIVERED').count()
    total_payment_pending=Order.objects.filter(payment_status='PENDING').count()
    total_cancel=Order.objects.filter(order_status='CANCELLED').count()
    total_orders=Order.objects.all().count()
    return render(request, 'dashboard/admin/orders-list.html',{'orders':orders,'total_shipped':total_shipped,'total_delivered':total_delivered,'total_payment_pending':total_payment_pending,'total_cancel':total_cancel,'total_orders':total_orders})

def order_detail(request, order_id):
    order=Order.objects.get(id=order_id)
    items=order.details.all()
    return render(request, 'dashboard/admin/order-detail.html', {'order':order, 'items':items})

def product_add(request):
    categories = ProductCategory.objects.all()
    sub_categories = ProductSubCategory.objects.all()
    image=request.FILES.get('product_image')
    if request.method == 'POST':
        category_id=request.POST.get('product_category')
        sub_category_id=request.POST.get('product_sub_category')
        if image:
            ext = os.path.splitext(image.name)[1].lower()
            if ext not in ['.jpg', '.jpeg', '.png']:
                return render(request, 'dashboard/admin/product-add.html', {
                    'categories': categories,
                    'sub_categories': sub_categories,
                    'error': 'Only JPG and PNG images are allowed.'
                })
        if not category_id or not sub_category_id:
            return render(request, 'dashboard/admin/product-add.html', {'categories': categories,'sub_categories':sub_categories,'error':'Please select both category and sub category.'})
        category=ProductCategory.objects.get(id=category_id)
        sub_category=ProductSubCategory.objects.get(id=sub_category_id)
        Product.objects.create(
            product_name=request.POST.get('product_name'),
            product_price=request.POST.get('product_price'),
            product_desc=request.POST.get('product_desc'),
            product_category=category,
            product_sub_category=sub_category,
            product_image=request.FILES.get('product_image'),
            product_madeof=request.POST.get('product_madeof'),
        )
        return redirect('dashboard:product_list')
    return render(request, 'dashboard/admin/product-add.html', {'categories': categories,'sub_categories':sub_categories})

def product_edit(request, product_id):
    product=Product.objects.get(id=product_id)
    categories = ProductCategory.objects.all()
    sub_categories = ProductSubCategory.objects.all()
    if request.method == 'POST':
        product.product_name=request.POST.get('product_name')
        product.product_price=request.POST.get('product_price')
        product.product_desc=request.POST.get('product_desc')
        category_id=request.POST.get('product_category')
        sub_category_id=request.POST.get('product_sub_category')
        product.product_category=ProductCategory.objects.get(id=category_id)
        product.product_sub_category=ProductSubCategory.objects.get(id=sub_category_id)
        product.product_madeof=request.POST.get('product_madeof')
        if request.FILES.get('product_image'):
            product.product_image=request.FILES.get('product_image')
        product.save()
        return redirect('dashboard:product_list')
    return render(request, 'dashboard/admin/product-edit.html', {'product': product,'categories': categories,'sub_categories':sub_categories})

def product_delete(request, product_id):
    product = Product.objects.get(id=product_id)
    product.delete()
    return redirect('shop_grid')

def product_list(request):
    products = Product.objects.all()
    query = request.GET.get('q')

    if query:
        products = products.filter(
            Q(product_name__icontains=query) |
            Q(product_desc__icontains=query)
        )

    return render(request, 'dashboard/admin/product-list.html', {'products': products})

def reduce_stock(product, qty):
    batches = product.batches.filter(quantity__gt=0).order_by('expiry_date')

    remaining = qty

    for batch in batches:
        if batch.quantity >= remaining:
            batch.quantity -= remaining
            batch.save()
            break
        else:
            remaining -= batch.quantity
            batch.quantity = 0
            batch.save()

def page(request, page_name):
    
    # handle sign-in POST
    if page_name == 'auth-signin' and request.method == 'POST':
        username = request.POST.get('username') or request.POST.get('Username')
        password = request.POST.get('password')
        next_url = request.POST.get('next') or request.GET.get('next') or reverse('dashboard:home')
        User=get_user_model()
        try:
            user_obj=User.objects.get(email=username)
            user=authenticate(request, username=user_obj.username, password=password)
        except User.DoesNotExist:
            user=None
        
        if user is not None:
            if user.is_staff:
                login(request, user)
                return redirect(next_url)
            else:
                return render(request, f'dashboard/admin/{page_name}.html', {'error': 'You do not have admin privileges.'})
        else:
            return render(request, f'dashboard/admin/{page_name}.html', {'error': 'Invalid email or password.'})

    # allow public pages like the sign-in page
    if page_name in PUBLIC_PAGES:
        return render(request, f'dashboard/admin/{page_name}.html')
    
    if not request.user.is_authenticated:
        signin_url = reverse('dashboard:page', kwargs={'page_name': 'auth-signin'})
        return redirect(f"{signin_url}?next={request.path}")

    # require admin/staff privileges
    if not request.user.is_staff:
        return HttpResponseForbidden('You do not have permission to access the dashboard.')

    return render(request, f'dashboard/admin/{page_name}.html')


def logout_view(request):
    logout(request)
    return redirect(reverse('dashboard:page', kwargs={'page_name': 'auth-signin'}))