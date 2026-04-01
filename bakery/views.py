from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.urls import reverse
from django.db.models import Q
from .forms import UserRegistrationForm, UserProfileForm, LoginForm
from django.contrib import messages
from allauth.socialaccount.models import SocialAccount
import razorpay
from django.conf import settings
import os
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.shortcuts import render,get_object_or_404,redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .utils import generate_otp, send_otp_email
from bakery.models import Product,UserProfile, Order, OrderDetail,ProductReview,OrderReturn,OrderReturnDetail,Coupon,CustomCakeOrder
from django.db import transaction
from django.http import HttpResponse
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from reportlab.platypus import Image
from reportlab.platypus import SimpleDocTemplate
from reportlab.platypus import Paragraph
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Spacer
from reportlab.platypus import Table
from reportlab.platypus import TableStyle
from datetime import timedelta

def customize_cake(request):
    if not request.user.is_authenticated:
        login_url=reverse('login')
        return redirect(f"{login_url}?next=/customize-cake/")
    return render(request, 'bakery/customize-cake.html')

def custom_checkout(request):
    if request.method == "POST":
        data = {
            "shape": request.POST.get("shape"),
            "layers": request.POST.get("layers"),
            "cream": request.POST.get("cream"),
            "filling_color": request.POST.get("filling_color"),
            "topping": request.POST.get("topping"),
            "cake_name": request.POST.get("cake_name"),
            "price": request.POST.get("price"),
            "weight": request.POST.get("weight"),
            "cake_image": request.POST.get("cake_image"),
        }
        return render(request, "bakery/custom-checkout.html", {"data": data})

def download_invoice(request, order_id):

    order = get_object_or_404(
        Order,
        id=order_id,
        user=request.user.profile
    )

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Invoice_{order.id}.pdf"'

    doc = SimpleDocTemplate(response, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()

    # ========================
    # HEADER (Logo + Company)
    # ========================

    logo_path = os.path.join(settings.MEDIA_ROOT, "favicon.png")  # Put logo in media folder

    if os.path.exists(logo_path):
        logo = Image(logo_path, width=1.5*inch, height=1*inch)
        elements.append(logo)

    elements.append(Paragraph("<b>TheSweetSpots</b>", styles['Title']))
    elements.append(Spacer(1, 12))

    # ========================
    # ORDER INFO
    # ========================

    elements.append(Paragraph(f"<b>Invoice #:</b> {order.id}", styles['Normal']))
    elements.append(Paragraph(f"<b>Order Date:</b> {order.order_date}", styles['Normal']))
    elements.append(Paragraph(f"<b>Payment Status:</b> {order.payment_status}", styles['Normal']))
    elements.append(Spacer(1, 12))

    # ========================
    # CUSTOMER DETAILS
    # ========================

    elements.append(Paragraph("<b>Bill To:</b>", styles['Heading3']))
    elements.append(Paragraph(f"Name: {order.user.user.username}", styles['Normal']))
    elements.append(Paragraph(f"Email: {order.user.user.email}", styles['Normal']))
    elements.append(Paragraph(f"Address: {order.user.address}", styles['Normal']))
    elements.append(Spacer(1, 12))

    # ========================
    # PRODUCT TABLE
    # ========================

    data = [['Product', 'Image', 'Qty', 'Price']]

    for item in order.details.all():

        img_path = item.product.product_image.path
        product_image = Image(img_path, width=0.8*inch, height=0.8*inch)

        data.append([
            item.product.product_name,
            product_image,
            str(item.qty),
            f"₹{item.product.product_price}"
        ])

    table = Table(data, colWidths=[150, 80, 50, 80])

    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))

    elements.append(table)
    elements.append(Spacer(1, 20))

    # ========================
    # PRICE CALCULATION
    # ========================

    if order.coupon:
        discount = order.discount_amount
    else:
        discount=0
    gst = order.gst_amount
    shipping = order.delivery_charge
    total = order.total_amount

    price_data = [
        ['Discount', f"- ₹{discount}"],
        ['GST', f"₹{gst}"],
        ['Shipping', f"₹{shipping}"],
        ['Total', f"₹{total}"],
    ]

    price_table = Table(price_data, colWidths=[200, 100])

    price_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
    ]))

    elements.append(price_table)
    elements.append(Spacer(1, 30))

    # ========================
    # FOOTER
    # ========================

    elements.append(Paragraph("<b>Thank you for shopping with TheSweetSpots!</b>", styles['Normal']))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph("Company Email: tss@gmail.com", styles['Normal']))
    elements.append(Paragraph("Customer Support: +91-XXXXXXXXXX", styles['Normal']))

    doc.build(elements)
    return response

def start_return(request, order_id):
    order = get_object_or_404(
        Order,
        id=order_id,
        user=request.user.profile,
        order_status='DELIVERED'
    )
    if not order.can_return():
        messages.error(request, "Return allowed only within 24 hours of delivery.")
        return redirect('my_orders')
    order_items = order.details.all()  # your order items

    if request.method == 'POST':
        with transaction.atomic():

            # create return entry
            order_return = OrderReturn.objects.create(order=order)

            for item in order_items:
                qty = int(request.POST.get(f'qty_{item.product.id}', 0))
                reason = request.POST.get(f'reason_{item.product.id}', '')

                if qty > 0:
                    OrderReturnDetail.objects.create(
                        order_return=order_return,
                        product=item.product,
                        qty=qty,
                        price=item.price,
                        reason_for_return=reason
                    )

            # update order status
            order.order_status = 'RETURNED'
            order.save()

        return redirect('my_orders')

    return render(request, 'bakery/return_order.html', {
        'order': order,
        'items': order_items
    })

def add_review(request, product_id):
    if not request.user.is_authenticated:
        return redirect('login')

    user_profile = UserProfile.objects.get(user=request.user)

    # Check if product was delivered
    delivered = OrderDetail.objects.filter(
        product_id=product_id,
        order__user=user_profile,
        order__order_status='DELIVERED'
    ).exists()

    if not delivered:
        return redirect('my-orders')  # safety check

    if request.method == "POST":
        rating = request.POST.get('rating')
        comment = request.POST.get('comment')

        ProductReview.objects.create(
            product_id=product_id,
            user=user_profile,
            rating=rating,
            comment=comment
        )
        return redirect('my_orders')

    return render(request, 'bakery/add-review.html')

def start_online_payment(request, order_id):
    try:
        order = Order.objects.get(id=order_id)
        amount=order.total_amount
    except Order.DoesNotExist:
        order=CustomCakeOrder.objects.get(id=order_id)
        amount=order.price

    client = razorpay.Client(
        auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
    )

    razorpay_order = client.order.create({
        "amount": int(float(amount) * 100),  # in paise
        "currency": "INR",
        "payment_capture": 1
    })

    order.payment_mode = 'PREPAID'
    order.save()

    context = {
        "order": order,
        "razorpay_key": settings.RAZORPAY_KEY_ID,
        "razorpay_order_id": razorpay_order['id'],
        "amount": int(float(amount) * 100)
    }

    return render(request, "bakery/razorpay-checkout.html", context)


def create_payment_link(request, order_id):
    # (Optional) If you want to create payment links, re-implement here.
    # For now, redirect to start_online_payment to use standard checkout flow.
    return redirect('start_online_payment', order_id=order_id)

def payment_cancel(request):
    order_id=request.GET.get('order_id')
    messages.error(request, "Payment was cancelled.")
    return redirect('checkout')

def payment_success(request):
    order_id = request.GET.get('order_id')
    order = Order.objects.get(id=order_id)
    order.payment_status = 'PAID'
    order.order_status = 'CONFIRMED'
    order.save()

    return render(request, 'bakery/order-success.html', {'order': order})

def user_profile(request):
    if not request.user.is_authenticated:
        login_url=reverse('login')
        return redirect(f"{login_url}?next=/profile/")
    user_profile = UserProfile.objects.get(user=request.user)
    orders = Order.objects.filter(user=user_profile).order_by('-order_date')

    context = {
        'profile': user_profile,
        'orders': orders,
    }
    return render(request, 'bakery/profile.html', context)

def cancel_order(request, order_id):
    order = get_object_or_404(
        Order,
        id=order_id,
        user=request.user.profile
    )

    # ❌ Block if shipped or delivered
    if order.order_status in ['SHIPPED', 'DELIVERED']:
        messages.error(request, "This order cannot be cancelled.")
        return redirect('my_orders')

    # ✅ Allow cancel
    order.order_status = 'CANCELLED'
    order.payment_status = 'REFUNDED'  # if prepaid
    order.save()

    messages.success(request, "Order cancelled successfully.")
    return redirect('my_orders')

@login_required
def my_orders(request):
    user_profile = request.user.profile
    orders = Order.objects.filter(user=user_profile).order_by('-id')

    return render(request, 'bakery/my-orders.html', {
        'orders': orders,
    })

@login_required
def my_order_detail(request, order_id):
    user_profile = request.user.profile
    order = Order.objects.get(id=order_id, user=user_profile)
    return render(request, 'bakery/my-order-detail.html', {
        'order': order
    })

def login_view(request):
    error=None
    social_account=None
    if request.user.is_authenticated:
        social_account=SocialAccount.objects.filter(user=request.user).first()

    if request.method=="POST":
        username=request.POST.get('username')
        password=request.POST.get('password')
        user=authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            next_url=request.GET.get('next')
            if next_url:
                return redirect(next_url)
            return redirect('shop_grid')
        else:
            error="Invalid username or password"
    return render(request, 'bakery/login.html', {'error': 'error','social_account': social_account})

def logout_view(request):
    logout(request)
    return redirect('login')

def forgot_password(request):
    error = None
    if request.method == "POST":
        email = request.POST.get("email")

        if not UserProfile.objects.filter(email=email).exists():
            error = "Email not registered"
        else:
            otp = generate_otp()
            request.session['reset_email'] = email
            request.session['email_otp'] = str(otp)

            send_otp_email(email, otp)

            return redirect('verify_otp')

    return render(request, 'bakery/forgot-password.html', {'error': error})

def verify_otp(request):
    error = None

    if request.method == "POST":
        entered_otp = request.POST.get("otp")
        saved_otp = request.session.get("email_otp")

        if entered_otp == saved_otp:
            return redirect('reset_password')
        else:
            error = "Invalid OTP"

    return render(request, 'bakery/verify-otp.html', {'error': error})

def reset_password(request):
    error = None

    if request.method == "POST":
        password = request.POST.get("password")
        confirm = request.POST.get("confirm_password")

        if password != confirm:
            error = "Passwords do not match"
        else:
            try:
                validate_password(password)
            except ValidationError as e:
                error= " ".join(e.messages)
            else:
                email = request.session.get('reset_email')
                profile = UserProfile.objects.get(email=email)
                user = profile.user

                user.set_password(password)
                user.save()

                request.session.flush()
                return redirect('login')
            
    return render(request, 'bakery/reset-password.html', {'error': error})


def my_account(request):
    if request.method == 'POST':
        user_form = UserRegistrationForm(request.POST)
        profile_form = UserProfileForm(request.POST)
        if user_form.is_valid() and profile_form.is_valid():
            user = user_form.save(commit=False)
            user.set_password(user_form.cleaned_data['password'])
            user.save()
            profile = profile_form.save(commit=False)
            profile.user = user
            profile.email = user.email
            profile.save()
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            return redirect('login')
    else:
        user_form = UserRegistrationForm()
        profile_form = UserProfileForm()
    return render(request, 'bakery/my-account.html', {
        'user_form': user_form,
        'profile_form': profile_form,
        
    })

def checkout(request):
    if not request.user.is_authenticated:
        login_url=reverse('login')
        return redirect(f"{login_url}?next=/checkout/")
    user_profile=request.user.profile
    cart = request.session.get('cart', {})

    is_custom = request.POST.get("is_custom")
    custom_data = None
    
    cart=request.session.get('cart', {})
    is_custom=request.POST.get("is_custom")

    if not cart and not is_custom:
        return redirect('cart')

    total_amount = sum(
        item['price'] * item['qty'] for item in cart.values()
    )
    GST_PERCENT = 5
    gst_amount = (total_amount*GST_PERCENT)/100
    discount = 0
    coupon_error = None
    applied_coupon = None

    today = timezone.now().date()
    coupons = Coupon.objects.filter(is_active=True, expiry_date__gte=today)

    if request.method == 'POST' and request.POST.get('action')=='apply_coupon':
        code = request.POST.get('coupon_code')

        try:
            coupon = Coupon.objects.get(code__iexact=code, is_active=True, expiry_date__gte=timezone.now().date())
            discount = coupon.discount_amount
            applied_coupon = coupon.code
        except Coupon.DoesNotExist:
            coupon_error = "Invalid coupon code or is Expired"
    
    if total_amount >= 100:
        delivery_charge = 0
    else:
        delivery_charge = 39

    if is_custom:
        custom_data = {
        "shape": request.POST.get("shape"),
        "layers": request.POST.get("layers"),
        "cream": request.POST.get("cream"),
        "topping": request.POST.get("topping"),
        "cake_name": request.POST.get("cake_name"),
        "price": request.POST.get("price"),
        "cake_image": request.POST.get("cake_image"),
    }

        grand_total = float(custom_data["price"])
    else:
        grand_total=total_amount+gst_amount+delivery_charge - discount
        if grand_total < 0:
            grand_total = 0

    if request.method == "POST" and request.POST.get('action')=='place_order':
        # create order
        user_profile=UserProfile.objects.get(user=request.user)
        payment_mode=request.POST.get("payment_mode")
        order = Order.objects.create(
            user=user_profile,
            total_amount=grand_total,
            delivery_charge=delivery_charge,
            gst_amount=gst_amount,
            payment_status='PENDING',
            payment_mode=payment_mode,
        )

        if is_custom:

            custom_order = CustomCakeOrder.objects.create(
                order=order,
                shape=request.POST.get("shape"),
                layers=request.POST.get("layers"),
                cream=request.POST.get("cream"),
                topping=request.POST.get("topping"),
                cake_name=request.POST.get("cake_name"),
                price=request.POST.get("price"),
                cake_image=request.POST.get("cake_image"),
                payment_method=payment_mode
    )

            if payment_mode == "ONLINE":
                if is_custom:
                   return redirect('start_online_payment', order_id=custom_order.id)
                else:
                    return redirect('start_online_payment', order_id=order.id)

            return redirect('custom_order_success', order_id=custom_order.id)

        # create order details
        for pid, item in cart.items():
            product = Product.objects.get(id=pid)
            if product.total_stock < item['qty']:
                return redirect()

            OrderDetail.objects.create(
                order=order,
                product=product,
                qty=item['qty'],
                price=item['price']
            )

            reduce_stock_fifo(product, item['qty'])
            product.save()

        # clear cart
        request.session['cart'] = {}
        request.session.modified = True

        if payment_mode=="ONLINE":
            return redirect('start_online_payment', order_id=order.id)

        return redirect('order_success', order_id=order.id)

    return render(request, 'bakery/checkout.html', {
        'cart': cart,
        'user_profile':user_profile,
        'total': total_amount,
        'grand_total':grand_total,
        'delivery_charge':delivery_charge,
        'gst_amount':gst_amount,
        'discount':discount,
        'coupons':coupons,
        'applied_coupon':applied_coupon,
        'coupon_error':coupon_error,
        'custom_data': custom_data
    })

def reduce_stock_fifo(product, qty):
    """
    Reduce stock using FIFO method (oldest expiry first)
    """

    # Get only valid (non-expired) batches
    batches = product.batches.filter(
        expiry_date__gte=timezone.now().date(),
        quantity__gt=0
    ).order_by('expiry_date')

    remaining_qty = qty

    for batch in batches:
        if remaining_qty <= 0:
            break

        if batch.quantity >= remaining_qty:
            batch.quantity -= remaining_qty
            batch.save()
            remaining_qty = 0
        else:
            remaining_qty -= batch.quantity
            batch.quantity = 0
            batch.save()

    if remaining_qty > 0:
        raise Exception("Not enough valid stock available")

def start_custom_online_payment(request,order_id):
    order = CustomCakeOrder.objects.get(id=order_id)
    if request.method == "POST":
        # your razorpay logic here
        return HttpResponse("Online Payment Started")

def order_success(request, order_id):
    order = Order.objects.filter(id=order_id).first()
    return render(request, 'bakery/order-success.html', {'order': order})

def shop_grid(request):
    query=request.GET.get('q')
    sort=request.GET.get('sort')
    products = Product.objects.all()
    if sort == 'low':
        products=products.order_by('product_price')
    elif sort == 'high':
        products=products.order_by('-product_price')
    elif sort == 'new':
        products=products.order_by('order_details')
    if query:
        products=products.filter( Q (product_name__icontains=query) | Q (product_desc__icontains=query))
    return render(request, 'bakery/shop-grid.html', {'products': products})

def index(request):
    products = Product.objects.all()
    cupcakes=Product.objects.filter(product_category_id=3)[:3]
    return render(request, 'bakery/index.html', {'products': products, 'cupcakes':cupcakes})

def menu(request):
    products = Product.objects.all()
    return render(request, 'bakery/menu.html', {'products': products})

def product_details(request, pk):
    product=get_object_or_404(Product, pk=pk)
    return render(request, 'bakery/product-details.html', {'product':product})

def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    cart= request.session.get('cart', {})
    pid=str(product_id)
    valid_stock = product.batches.filter(
    expiry_date__gte=timezone.now().date(),
    quantity__gt=0,
    expiry_date__lte=timezone.now().date() + timedelta(days=2)
)
    current_qty=cart.get(pid,{}).get('qty',0)
    if current_qty + 1 > 3:
        messages.warning(request,"You can only order maximum 3 items of this product.")
        return redirect('cart')
    if current_qty + 1 > product.total_stock:
        messages.warning(request,f"we only have {product.total_stock} item(s) left in stock.")
        return redirect('cart')
    if pid in cart:
        cart[pid]['qty'] += 1
    else:
        cart[pid] = {
            'name': product.product_name,
            'price': float(product.product_price),
            'desc': product.product_desc,
            'qty': 1,
            'image': product.product_image.url if product.product_image else ''
        }
    request.session['cart'] = cart
    request.session.modified = True
    return redirect('cart')

def view_cart(request):
    cart = request.session.get('cart', {})
    total = sum(item['price'] * item['qty'] for item in cart.values())
    GST_PERCENT = 5
    gst_amount = (total*GST_PERCENT)/100
    if total >= 100:
        delivery_charge = 0
    else:
        delivery_charge = 39
    grand_total=total+gst_amount+delivery_charge
    # build a list of items with key and subtotal for template convenience
    cart_items = []
    for key, item in cart.items():
        item_copy = item.copy()
        item_copy['key'] = key
        item_copy['subtotal'] = item_copy['price'] * item_copy['qty']
        cart_items.append(item_copy)
    return render(request, 'bakery/cart.html', {'cart_items': cart_items, 'cart': cart, 'total': total,'grand_total':grand_total,'delivery_charge':delivery_charge,'gst_amount':gst_amount})

def update_cart_qty(request, product_id, action):
    product = get_object_or_404(Product, id=product_id)
    cart=request.session.get('cart', {})
    pid=str(product_id)
    current_qty=cart.get(pid,{}).get('qty',0)
    if pid in cart:
        if action=='inc':
            if current_qty + 1 > 3:
                messages.warning(request,"You can only order maximum 3 items of this product.")
                return redirect('cart')
            if current_qty + 1 > product.total_stock:
                messages.warning(request,f"we only have {product.total_stock} item(s) left in stock.")
                return redirect('cart')
            cart[pid]['qty'] += 1
        elif action=='dec':
            cart[pid]['qty'] -= 1
            if cart[pid]['qty'] <= 0:
                del cart[pid]
    request.session['cart'] = cart
    request.session.modified = True
    return redirect('cart')

def remove_from_cart(request, product_id):
    cart=request.session.get('cart', {})
    pid=str(product_id)
    if pid in cart:
        del cart[pid]
    request.session['cart'] = cart
    request.session.modified = True
    return redirect('cart')

def add_to_wishlist(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    wishlist = request.session.get('wishlist', [])
    if product_id in wishlist:
        wishlist.remove(product_id)
    else:
        wishlist.append(product_id)
    request.session['wishlist'] = wishlist
    request.session.modified = True
    return redirect(request.META.get('HTTP_REFERER', 'shop_grid'))

def remove_from_wishlist(request, product_id):
    wishlist = request.session.get('wishlist', [])
    if product_id in wishlist:
        wishlist.remove(product_id)
    request.session['wishlist'] = wishlist
    request.session.modified = True
    return redirect('wishlist')

def wishlist_view(request):
    wishlist_ids = request.session.get('wishlist', [])
    products = Product.objects.filter(id__in=wishlist_ids)
    return render(request, 'bakery/wishlist.html', {'products': products})

def page(request, page_name):
    wishlist= request.session.get('wishlist', [])
    wishlist_count=len(wishlist)
    return render(request, f'bakery/{page_name}.html',{'wishlist_count':wishlist_count})

def page(request, page_name):
    return render(request, f'bakery/{page_name}.html')
# Create your views here.
