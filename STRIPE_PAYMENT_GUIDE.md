# Stripe Payment Integration Guide - Artvinci

## 📋 Overview

This document describes the complete shopping cart (panier) and Stripe payment integration for the Artvinci platform.

## 🎯 Features Implemented

### Backend (Django + MongoDB)

1. **New `ventes` App** - Sales Management

   - Order model with embedded OrderItems
   - Stripe Payment Intent creation
   - Payment confirmation and order completion
   - Order history management
   - Artist sales tracking

2. **Models**

   - `Order`: Main order document with user, items, total, status, payment info
   - `OrderItem`: Embedded document for each artwork in order

3. **API Endpoints**
   - `POST /api/ventes/create-payment-intent/` - Create Stripe payment intent
   - `POST /api/ventes/confirm-payment/` - Confirm payment after Stripe success
   - `GET /api/ventes/config/` - Get Stripe publishable key
   - `GET /api/ventes/orders/` - Get user's orders
   - `GET /api/ventes/orders/<id>/` - Get specific order details
   - `GET /api/ventes/sales/` - Get artist's sales

### Frontend (React)

1. **Cart Context** - Global shopping cart state management

   - Add/remove items
   - Update quantities
   - Calculate totals
   - Persist in localStorage

2. **Components**
   - `AddToCartButton` - Button to add artworks to cart
   - `CartIcon` - Shows cart count in navbar
   - `Cart` - Shopping cart page
   - `Checkout` - Stripe payment form
   - `Orders` - Order history
   - `OrderDetail` - Detailed order view

## 🚀 Setup Instructions

### Backend Setup

1. **Install Stripe Python library**

   ```bash
   cd c:\Users\judos\Desktop\Artvinci-backend
   pip install stripe==8.0.0
   ```

2. **Environment variables are already configured in `.env`**:

   ```env
   STRIPE_PUBLISHABLE_KEY=your_stripe_publishable_key_here
   STRIPE_SECRET_KEY=your_stripe_secret_key_here
   ```

   **Note**: The actual keys are stored in your `.env` file and should never be committed to Git.

3. **The `ventes` app is already added to `INSTALLED_APPS`** in `settings.py`

4. **URLs are configured** in `artvinci/urls.py`

### Frontend Setup

1. **Install Stripe dependencies**

   ```bash
   cd c:\Users\judos\Desktop\Artvinci-Frontend
   npm install @stripe/stripe-js @stripe/react-stripe-js
   ```

2. **The cart context and routes are already configured** in `App.jsx`

## 📝 How It Works

### User Flow

1. **Browse Gallery**

   - User views artworks in the gallery
   - Each artwork has an "Add to Cart" button

2. **Add to Cart**

   - User clicks "Add to Cart"
   - Artwork is added to cart context
   - Cart count badge updates in navbar
   - Toast notification confirms addition

3. **View Cart**

   - User clicks cart icon in navbar
   - Sees all items in cart
   - Can modify quantities or remove items
   - Sees total price calculation

4. **Checkout**

   - User clicks "Proceed to Checkout"
   - Redirected to login if not authenticated
   - Enters shipping information
   - Payment form loads with Stripe Elements

5. **Payment**

   - Backend creates Stripe Payment Intent
   - User enters card details
   - Stripe securely processes payment
   - On success, backend confirms order
   - Artworks marked as sold
   - User redirected to order confirmation

6. **Order History**
   - User can view all orders in `/orders`
   - Filter by status (pending, completed, etc.)
   - View detailed order information

## 🔒 Security Features

- **No webhook required** - Simplified implementation
- **Stripe handles PCI compliance** - Card details never touch your server
- **JWT authentication** - Secure API endpoints
- **User ownership validation** - Users can only see their own orders
- **Payment verification** - Backend confirms payment with Stripe before marking complete

## 💳 Test Cards (Stripe Test Mode)

Use these cards for testing:

- **Success**: `4242 4242 4242 4242`
- **Decline**: `4000 0000 0000 0002`
- **3D Secure**: `4000 0025 0000 3155`

- Use any future expiry date (e.g., `12/34`)
- Use any 3-digit CVC
- Use any postal code

## 📊 Database Schema

### Order Collection

```javascript
{
  _id: ObjectId,
  user: Reference(User),
  items: [
    {
      artwork: Reference(Artwork),
      quantity: Number,
      price: Decimal
    }
  ],
  total_price: Decimal,
  currency: String,
  status: String, // 'pending', 'completed', 'cancelled', 'refunded'
  payment_intent_id: String,
  payment_method: String,
  shipping_address: String,
  phone_number: String,
  notes: String,
  created_at: DateTime,
  updated_at: DateTime,
  completed_at: DateTime
}
```

## 🎨 Cart Features

- **Persistent Cart** - Saved in localStorage
- **Quantity Management** - Increase/decrease quantities
- **Real-time Totals** - Automatic calculation
- **Remove Items** - Individual or clear all
- **Cart Badge** - Shows item count in navbar
- **Toast Notifications** - User feedback for actions

## 🔄 Status Flow

1. **Pending** - Order created, payment not completed
2. **Completed** - Payment successful, artworks marked as sold
3. **Cancelled** - Order cancelled by user/admin
4. **Refunded** - Payment refunded

## 📱 Routes Added

### Frontend Routes

- `/cart` - Shopping cart page
- `/checkout` - Payment checkout (protected)
- `/orders` - Order history (protected)
- `/orders/:orderId` - Order details (protected)

### Backend Routes

- `/api/ventes/config/` - Get Stripe config
- `/api/ventes/create-payment-intent/` - Create payment
- `/api/ventes/confirm-payment/` - Confirm payment
- `/api/ventes/orders/` - List orders
- `/api/ventes/orders/<id>/` - Order detail
- `/api/ventes/sales/` - Artist sales

## 🎯 Next Steps (Optional Enhancements)

1. **Add Webhooks** - For better payment confirmation
2. **Email Notifications** - Order confirmations
3. **Invoice Generation** - PDF invoices
4. **Refund Support** - Allow refunds through admin
5. **Multiple Currencies** - Support EUR, GBP, etc.
6. **Shipping Integration** - Calculate shipping costs
7. **Tax Calculation** - Add tax support
8. **Order Tracking** - Shipping status updates
9. **Reviews** - Allow buyers to review purchased art
10. **Artist Dashboard** - Enhanced sales analytics

## 📞 Support

For issues or questions:

- Check Stripe Dashboard for payment details
- Review browser console for errors
- Check Django logs for backend errors
- Verify MongoDB collections for data

## ✅ Testing Checklist

- [ ] Add artwork to cart
- [ ] View cart with multiple items
- [ ] Update quantities
- [ ] Remove items
- [ ] Cart persists on page refresh
- [ ] Checkout flow works
- [ ] Payment processes successfully
- [ ] Order appears in history
- [ ] Artwork marked as sold
- [ ] Artist can see sales
- [ ] Order details display correctly

---

**Implementation Date**: October 28, 2025
**Framework**: Django 4.2.7 + React + Stripe API v8
**Database**: MongoDB with MongoEngine
