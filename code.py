from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import logout
from django.core.paginator import Paginator
from django.conf import settings

import hashlib
import os
import json
import qrcode
from web3 import Web3

from userapp.models import User, Feedback, CartItem
from adminapp.models import MedicineAdmin, BkModel, TransactionReceipt
from ethicareproject.BlockcahinAlgo import HashDataBlock


# ------------------------------
# Admin Logout
# ------------------------------
def admin_logout(request):
    logout(request)
    return redirect('adminlogin')


# ------------------------------
# Admin Dashboard
# ------------------------------
def admin_dashboard(request):
    total_medicines = MedicineAdmin.objects.all().count()
    total_users = User.objects.all().count()
    total_feedbacks = Feedback.objects.all().count()

    context = {
        'total_medicines': total_medicines,
        'total_users': total_users,
        'total_feedbacks': total_feedbacks,
    }
    return render(request, "admin/index.html", context)


# ------------------------------
# View All Medicines
# ------------------------------
def all_medicines(request):
    all_medicines = MedicineAdmin.objects.all()
    return render(request, "admin/view-medicines.html", {'all_medicines': all_medicines})


# ------------------------------
# Edit Medicines
# ------------------------------
def edit_medicines(request, medicine_id):
    medicine = get_object_or_404(MedicineAdmin, id=medicine_id)

    if request.method == 'POST':
        # Update medicine details
        medicine.medicine_name = request.POST.get('medicineName')
        medicine.medicine_type = request.POST.get('medicineType')
        medicine.medicine_price = request.POST.get('medicinePrice')
        medicine.distributor = request.POST.get('distributor')
        medicine.medicine_formula = request.POST.get('medicineFormula')
        medicine.expiry_date = request.POST.get('expiryDate')
        medicine.manufacture_date = request.POST.get('manufacturedate')
        medicine.manufacture = request.POST.get('manufacture')
        medicine.dosage_information = request.POST.get('dosageInformation')
        medicine.storage_conditions = request.POST.get('storageConditions')

        # Update medicine image
        medicine_image = request.FILES.get('image')
        if medicine_image:
            medicine.medicine_image = medicine_image

        medicine.save()

        # Update Blockchain Hashes
        bk_model_instance, created = BkModel.objects.get_or_create(medicine=medicine)
        bk_model_instance.distributor_hash = hashlib.sha256(medicine.distributor.encode()).hexdigest()
        bk_model_instance.manufacture_hash = hashlib.sha256(medicine.manufacture.encode()).hexdigest()
        bk_model_instance.expiry_date_hash = hashlib.sha256(medicine.expiry_date.encode('utf-8')).hexdigest()
        bk_model_instance.price_hash = hashlib.sha256(str(medicine.medicine_price).encode()).hexdigest()
        bk_model_instance.formula_hash = hashlib.sha256(medicine.medicine_formula.encode()).hexdigest()
        bk_model_instance.type_hash = hashlib.sha256(medicine.medicine_type.encode()).hexdigest()
        bk_model_instance.save()

        messages.success(request, 'Medicine updated successfully.')
        return redirect('admin_edit_medicines', medicine_id=medicine_id)

    return render(request, "admin/edit-medicines.html", {'medicine': medicine})


# ------------------------------
# View Orders
# ------------------------------
def view_orders(request):
    ordered_cart_items_list = CartItem.objects.filter(status='ordered').select_related('user', 'medicine', 'order')
    paginator = Paginator(ordered_cart_items_list, 10)
    page_number = request.GET.get('page')
    ordered_cart_items = paginator.get_page(page_number)
    return render(request, "admin/view-orders.html", {'ordered_cart_items': ordered_cart_items})


# ------------------------------
# View Feedbacks
# ------------------------------
def view_feedbacks(request):
    feedbacks_list = Feedback.objects.select_related('Order', 'user').all()
    paginator = Paginator(feedbacks_list, 5)
    page_number = request.GET.get('page')
    feedbacks = paginator.get_page(page_number)
    return render(request, "admin/view-feedbacks.html", {'feedbacks': feedbacks})


# ------------------------------
# Feedback Graph
# ------------------------------
def feedback_graph(request):
    rating_counts = {
        'rating1': Feedback.objects.filter(rating=1).count(),
        'rating2': Feedback.objects.filter(rating=2).count(),
        'rating3': Feedback.objects.filter(rating=3).count(),
        'rating4': Feedback.objects.filter(rating=4).count(),
        'rating5': Feedback.objects.filter(rating=5).count(),
    }
    return render(request, "admin/graph.html", {'rating_counts': rating_counts})


# ------------------------------
# View All Users
# ------------------------------
def all_users(request):
    all_users = User.objects.all()
    paginator = Paginator(all_users, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, "admin/all-users.html", {'all_users': page_obj})


# ------------------------------
# Delete Medicine
# ------------------------------
def delete_medicine(request, medicine_id):
    medicine = MedicineAdmin.objects.get(id=medicine_id)
    medicine.delete()
    messages.success(request, "Medicine removed successfully.")
    return redirect('admin_all_medicines')


# ------------------------------
# Ethereum Connection
# ------------------------------
web3 = Web3(Web3.HTTPProvider('http://127.0.0.1:7545'))
if web3.is_connected():
    print("Connected to Ethereum client")
    print("Network ID:", web3.net.version)
else:
    print("Failed to connect to Ethereum client")

with open('ethereum/build/contracts/MedicineContract.json', 'r') as file:
    contract_json = json.load(file)
contract_abi = contract_json['abi']
contract_address = contract_json['networks']['5777']['address']
contract = web3.eth.contract(address=contract_address, abi=contract_abi)


# ------------------------------
# Add Medicines
# ------------------------------
def add_medicines(request):
    if request.method == 'POST':
        medicine_name = request.POST.get('medicineName')
        medicine_type = request.POST.get('medicineType')
        medicine_price = int(request.POST.get('medicinePrice'))
        distributor = request.POST.get('distributor')
        medicine_formula = request.POST.get('medicineFormula')
        expiry_date = request.POST.get('expiryDate')
        manufacture_date = request.POST.get('manufacturedate')
        manufacture = request.POST.get('manufacture')
        dosage_information = request.POST.get('dosageInformation')
        storage_conditions = request.POST.get('storageConditions')
        medicine_image = request.FILES.get('image')

        # Check if medicine exists
        if MedicineAdmin.objects.filter(medicine_name=medicine_name, medicine_type=medicine_type).exists():
            messages.error(request, 'Medicine already exists.')
            return redirect('add_medicines')

        # Create MedicineAdmin instance
        new_medicine = MedicineAdmin.objects.create(
            medicine_name=medicine_name,
            medicine_type=medicine_type,
            medicine_price=medicine_price,
            distributor=distributor,
            medicine_formula=medicine_formula,
            expiry_date=expiry_date,
            manufacture_date=manufacture_date,
            manufacture=manufacture,
            dosage_information=dosage_information,
            storage_conditions=storage_conditions,
            medicine_image=medicine_image,
        )

        # Blockchain transaction
        from_account = web3.eth.accounts[0]
        nonce = web3.eth.get_transaction_count(from_account)
        tx_dict = {
            'from': from_account,
            'nonce': nonce,
            'gas': 2000000,
            'gasPrice': web3.to_wei('20', 'gwei'),
            'to': contract_address,
            'data': contract.encodeABI(
                fn_name='addMedicine',
                args=[
                    medicine_name, medicine_type, medicine_price, distributor,
                    medicine_formula, expiry_date, manufacture_date, manufacture,
                    dosage_information, storage_conditions
                ]
            ),
        }
        private_key = 'YOUR_PRIVATE_KEY'  # Replace with your actual private key
        signed_tx = web3.eth.account.sign_transaction(tx_dict, private_key)
        tx_hash = web3.eth.send_raw_transaction(signed_tx.rawTransaction)
        tx_receipt = web3.eth.wait_for_transaction_receipt(tx_hash)

        # Create TransactionReceipt
        TransactionReceipt.objects.create(
            medicine=new_medicine,
            transaction_hash=tx_receipt['transactionHash'].hex(),
            from_address=tx_receipt['from'],
            to_address=tx_receipt['to'],
            gas_used=tx_receipt['gasUsed'],
            cumulative_gas_used=tx_receipt['cumulativeGasUsed'],
            effective_gas_price=tx_receipt['effectiveGasPrice'],
            transaction_status=tx_receipt['status'] == 1,
            transaction_type=tx_receipt['type'],
        )

        # QR Code Generation
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr_data = (
            f"Name: {medicine_name}\n"
            f"Type: {medicine_type}\n"
            f"Price: {medicine_price}\n"
            f"Distributor: {distributor}\n"
            f"Formula: {medicine_formula}\n"
            f"Expiry Date: {expiry_date}\n"
            f"Manufacture Date: {manufacture_date}\n"
            f"Manufacture: {manufacture}\n"
            f"Dosage Information: {dosage_information}\n"
            f"Storage Conditions: {storage_conditions}"
        )
        qr.add_data(qr_data)
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="black", back_color="white")

        qr_folder_path = os.path.join(settings.MEDIA_ROOT, 'medicine_qr_codes')
        os.makedirs(qr_folder_path, exist_ok=True)
        safe_medicine_name = "".join(x for x in medicine_name if x.isalnum())
        qr_file_path = os.path.join(qr_folder_path, f'{safe_medicine_name}.png')
        qr_img.save(qr_file_path)

        new_medicine.qr_code = os.path.join('medicine_qr_codes', f'{safe_medicine_name}.png')
        new_medicine.save()

        # BkModel Blockchain Hashes
        BkModel.objects.create(
            medicine=new_medicine,
            distributor_hash=hashlib.sha256(distributor.encode('utf-8')).hexdigest(),
            manufacture_hash=hashlib.sha256(manufacture.encode('utf-8')).hexdigest(),
            expiry_date_hash=hashlib.sha256(expiry_date.encode('utf-8')).hexdigest(),
            price_hash=hashlib.sha256(str(medicine_price).encode('utf-8')).hexdigest(),
            formula_hash=hashlib.sha256(medicine_formula.encode('utf-8')).hexdigest(),
            type_hash=hashlib.sha256(medicine_type.encode('utf-8')).hexdigest(),
            medicine_name_hash=hashlib.sha256(medicine_name.encode('utf-8')).hexdigest(),
            medicine_type_hash=hashlib.sha256(medicine_type.encode('utf-8')).hexdigest(),
        )

        messages.success(request, "Medicine added successfully with QR code and blockchain transaction.")
        return redirect('add_medicines')

    return render(request, 'admin/add-medicines.html')


# ------------------------------
# Paginated Medicines View
# ------------------------------
def all_medicines2(request):
    all_medicines = MedicineAdmin.objects.all()
    paginator = Paginator(all_medicines, 5)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    return render(request, "admin/all-medicines.html", {'medicines': page_obj})


# ------------------------------
# Admin Remove Medicine
# ------------------------------
def admin_remove_medicine(request, medicine_id):
    medicine = MedicineAdmin.objects.get(id=medicine_id)
    medicine.delete()
    messages.success(request, "Medicine removed successfully.")
    return redirect('admin_all_medicines')


# ------------------------------
# Change User Status
# ------------------------------
def change_user_status(request, user_id):
    user = get_object_or_404(User, pk=user_id)
    if user.status == 'accepted':
        user.status = 'rejected'
        messages.success(request, "User status has been changed to rejected.")
    else:
        user.status = 'accepted'
        messages.success(request, "User status has been changed to accepted.")
    user.save()
    return redirect('all_hospitals')


# ------------------------------
# Remove User
# ------------------------------
def remove_user(request, user_id):
    user = get_object_or_404(User, pk=user_id)
    user.delete()
    messages.success(request, "User has been removed successfully.")
    return redirect('all_hospitals')
