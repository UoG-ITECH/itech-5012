from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views import View
from datetime import datetime


from rango.models import Category, Product, UserProfile
from rango.forms import CategoryForm, ProductForm, UserForm, UserProfileForm, ReviewForm
from rango.bing_search import run_query


class IndexView(View):
    def get(self, request):
        category_list = Category.objects.order_by('-name')[:5]
        product_list = Product.objects.order_by('-name')[:5]

        context_dict = {}
        context_dict['boldmessage'] = 'Crunchy, creamy, cookie, candy, cupcake!'
        context_dict['categories'] = category_list
        context_dict['products'] = product_list

        visitor_cookie_handler(request)

        response = render(request, 'rango/index.html', context=context_dict)
        return response


class AboutView(View):
    def get(self, request):
        context_dict = {}
        visitor_cookie_handler(request)
        context_dict['visits'] = request.session['visits']

        return render(request, 'rango/about.html', context=context_dict)


def search(request):
    result_list = []
    query = ''
    if request.method == 'POST':
        query = request.POST['query'].strip()

        if query:
            result_list = run_query(query)

    return render(request, 'rango/search.html', {
        'result_list': result_list,
        'query': query
    })


class ShowCategoryView(View):
    def create_context_dict(self, category_name_slug):
        context_dict = {}
        try:
            category = Category.objects.get(slug=category_name_slug)
            products = Product.objects.filter(category=category).order_by('-name')

            context_dict['products'] = products
            context_dict['category'] = category
        except Category.DoesNotExist:
            context_dict['products'] = None
            context_dict['category'] = None

        return context_dict

    def get(self, request, category_name_slug):
        context_dict = self.create_context_dict(category_name_slug)
        return render(request, 'rango/category.html', context_dict)

    @method_decorator(login_required)
    def post(self, request, category_name_slug):
        context_dict = self.create_context_dict(category_name_slug)
        query = request.POST['query'].strip()

        if query:
            context_dict['result_list'] = run_query(query)
            context_dict['query'] = query

        return render(request, 'rango/category.html', context_dict)


class AddCategoryView(View):
    @method_decorator(login_required)
    def get(self, request):
        form = CategoryForm()
        return render(request, 'rango/add_category.html', {'form': form})

    @method_decorator(login_required)
    def post(self, request):
        form = CategoryForm(request.POST)

        if form.is_valid():
            form.save(commit=True)
            return redirect(reverse('rango:index'))
        else:
            print(form.errors)

        return render(request, 'rango/add_category.html', {'form': form})


class ShowProductView(View):
    def get(self, request, slug):
        context_dict = {}

        try:
            product = Product.objects.get(slug=slug)

            context_dict['product'] = product

        except Product.DoesNotExist:
            context_dict['product'] = product

        context_dict['pathimg'] = "images/" + str(product.slug) + ".jpg"
        print("images/" + str(product.slug) + ".jpg")
        return render(request, 'rango/product.html', context=context_dict)


class AddProductView(View):
    def get_category_name(self, category_name_slug):
        try:
            category = Category.objects.get(slug=category_name_slug)
        except Category.DoesNotExist:
            category = None

        return category

    @method_decorator(login_required)
    def get(self, request, category_name_slug):
        form = ProductForm()
        category = self.get_category_name(category_name_slug)

        if category is None:
            return redirect(reverse('rango:index'))

        context_dict = {'form': form, 'category': category}
        return render(request, 'rango/add_product.html', context_dict)

    @method_decorator(login_required)
    def post(self, request, category_name_slug):
        form = ProductForm(request.POST)
        category = self.get_category_name(category_name_slug)

        if category is None:
            return redirect(reverse('rango:index'))

        if form.is_valid():
            if category:
                product = form.save(commit=False)
                product.category = category
                product.views = 0
                if 'picture' in request.FILES:
                    product.picture = request.FILES['picture']
                product.save()
                print(product)

                return redirect(reverse('rango:show_category',
                                        kwargs={'category_name_slug':
                                                    category_name_slug}))
        else:
            print(form.errors)

        context_dict = {'form': form, 'category': category}
        return render(request, 'rango/add_product.html', context=context_dict)


class ProfileView(View):
    @method_decorator(login_required)
    def get(self, request):
        profile = UserProfile.objects.get(user__username=request.user.username)
        return render(request, 'rango/profile.html', {'profile': profile})

    # TODO: functionality to modify profile
    # @method_decorator(login_required)
    # def post(self, request):


def goto_url(request):
    if request.method == 'GET':
        page_id = request.GET.get('page_id')

        try:
            selected_page = Page.objects.get(id=page_id)
        except Page.DoesNotExist:
            return redirect(reverse('rango:index'))

        selected_page.views = selected_page.views + 1
        selected_page.save()

        return redirect(selected_page.url)

    return redirect(reverse('rango:index'))


@login_required
def register_profile(request):
    form = UserProfileForm()

    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES)

        if form.is_valid():
            user_profile = form.save(commit=False)
            user_profile.user = request.user
            user_profile.save()

            return redirect(reverse('rango:index'))
        else:
            print(form.errors)

    context_dict = {'form': form}
    return render(request, 'rango/profile_registration.html', context_dict)


def register(request):
    registered = False
    if request.method == 'POST':
        user_form = UserForm(request.POST)
        profile_form = UserProfileForm(request.POST)

        if user_form.is_valid() and profile_form.is_valid():
            user = user_form.save()
            user.set_password(user.password)
            user.save()

            profile = profile_form.save(commit=False)
            profile.user = user

            if 'picture' in request.FILES:
                profile.picture = request.FILES['picture']
            profile.save()
            registered = True
        else:
            print(user_form.errors, profile_form.errors)
    else:
        user_form = UserForm()
        profile_form = UserProfileForm()

    return render(request,
                  'rango/register.html',
                  context={'user_form': user_form,
                           'profile_form': profile_form,
                           'registered': registered})


def user_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(username=username, password=password)

        if user:
            if user.is_active:
                login(request, user)
                return redirect(reverse('rango:index'))
            else:
                return HttpResponse("Your Rango account is disabled.")
        else:
            print(f"Invalid login details: {username}, {password}")
            return HttpResponse("Invalid login details supplied.")
    else:
        return render(request, 'rango/login.html')


class AddReviewView(View):

    @method_decorator(login_required)
    def get(self, request, slug):
        form = ReviewForm()
        product = Product.objects.get(slug=slug)

        if product is None:
            return redirect(reverse('rango:index'))

        context_dict = {'form': form, 'product': product}
        return render(request, 'rango/review.html', context=context_dict)

    def post(self, request, slug):
        form = ReviewForm(request.POST)
        product = Product.objects.get(slug=slug)

        if product is None:
            return redirect(reverse('rango:index'))
        if form.is_valid():
            if product:
                review = form.save(commit=False)
                review.product = product
                review.user = request.user
                review.save()
                return redirect(reverse('rango:index'))
        else:
            print(form.errors)

        context_dict = {'form': form, 'product': product}
        return render(request, 'rango/review.html', context=context_dict)


@login_required
def restricted(request):
    return render(request, 'rango/restricted.html')


@login_required
def user_logout(request):
    logout(request)
    return redirect(reverse('rango:index'))


def get_server_side_cookie(request, cookie, default_val=None):
    val = request.session.get(cookie)
    if not val:
        val = default_val
    return val


def visitor_cookie_handler(request):
    visits = int(get_server_side_cookie(request, 'visits', '1'))
    last_visit_cookie = get_server_side_cookie(request,
                                               'last_visit',
                                               str(datetime.now()))
    last_visit_time = datetime.strptime(last_visit_cookie[:-7],
                                        '%Y-%m-%d %H:%M:%S')

    if (datetime.now() - last_visit_time).days > 0:
        visits = visits + 1
        request.session['last_visit'] = str(datetime.now())
    else:
        request.session['last_visit'] = last_visit_cookie

    request.session['visits'] = visits
