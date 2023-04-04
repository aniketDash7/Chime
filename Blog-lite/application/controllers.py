import secrets
import os
from flask import render_template, flash, redirect, url_for, request, abort
from application import app, db, bcrypt
from application.forms import RegistrationForm, LoginForm, PostForm, updateAccountForm, FollowForm, SearchForm
from application.models import User, Post, followers, Comment, Like
from flask_login import login_user, current_user, logout_user, login_required
from datetime import datetime, date, time


@app.route('/')
@login_required
def home():
    feedPosts = current_user.followed_posts()

    user_query = request.args.get('user_query')
    if user_query:
        searched_user = User.query.filter(User.username.contains(user_query))
    else:
        searched_user = User.query.all()
    
    return render_template('home.html',users=searched_user, feedPosts=feedPosts)


@app.route('/register',methods=['POST','GET'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(username=form.username.data, password=hashed_password) 
        db.session.add(user)
        db.session.commit()
        flash(f'Account created for {form.username.data}!','success')
        return redirect(url_for('login'))
    return render_template('register.html',form=form)


@app.route('/login',methods=['POST','GET'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user)
            next_page = request.args.get('next')
            flash('You have been logged in ', 'success')
            return redirect(next_page) if next_page else redirect(url_for('home'))
        else:
            flash('Login Unsuccessful','danger') 

    return render_template('login.html',form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('home'))


@app.route('/profile/<username>')
def profile(username):

    form=FollowForm()

    user=User.query.filter_by(username=username).first()
    users=User.query.all()
    image = url_for('static', filename='profilePics/' + user.propic)
    profile_posts = Post.query.filter_by(user_id=user.id)

    postNum = profile_posts.count()
    followNum = user.followers.count()

    return render_template('profile.html',user=user,profile_posts=profile_posts,postNum=postNum, followNum=followNum,users=users,image=image,form=form)


def savingPicture(upImage):
    random_hex = secrets.token_hex(8)
    name,extension = os.path.splitext(upImage.filename)
    picFile = random_hex + extension
    path = os.path.join(app.root_path, 'static/images', picFile)
    upImage.save(path)
    return picFile

def deletingPicture(image):

    file_path = os.path.join(app.root_path, 'static/images', image)
    if os.path.isfile(file_path):
        os.remove(file_path)
    else:
        return "File does not exist"


@app.route('/newpost', methods=['GET','POST'])
@login_required
def post():
    form = PostForm()
    if form.validate_on_submit():
        post = Post(title=form.title.data, desc=form.desc.data, author=current_user)
        if form.imageUrl.data:
            image_file = savingPicture(form.imageUrl.data)
            post.imageUrl = image_file
        db.session.add(post)
        db.session.commit()
        flash('Your post has been created !', 'Success')
        return redirect(url_for('home'))
    return render_template('make_post.html',form=form, legend='New Post')


@app.route('/post/<int:id>')
def zoomPost(id):
    post = Post.query.get_or_404(id)
    return render_template('post.html',title=post.title, post=post)


@app.route('/post/<int:id>/update', methods=['POST','GET'])
@login_required
def updatePost(id):
    post = Post.query.get_or_404(id)
    if post.author != current_user:
        abort(403)
    form = PostForm()
    if form.validate_on_submit():
        post.title = form.title.data
        post.desc = form.desc.data
        if form.imageUrl.data:
            image_file = savingPicture(form.imageUrl.data)
            post.imageUrl = image_file
        post.timeStamp = datetime.utcnow()
        db.session.commit()
        flash('Your post has been updated','success')
        return redirect(url_for('zoomPost',id=post.id))
    elif request.method == 'GET':     
        form.title.data = post.title
        form.desc.data = post.desc
        if form.imageUrl.data:
            form.imageUrl.data = post.imageUrl
    return render_template('make_post.html',form=form,legend='Update Post')
    
    

def savingProPicture(upImage):
    random_hex = secrets.token_hex(8)
    name,extension = os.path.splitext(upImage.filename)
    picFile = random_hex + extension
    path = os.path.join(app.root_path, 'static/profilePics', picFile)
    upImage.save(path)
    return picFile

def deleteProPicture(image):
    file_path = os.path.join(app.root_path, 'static/profilePics', image)
    if os.path.isfile(file_path):
        os.remove(file_path)
    else:
        return "File does not exist"


@app.route("/account", methods=['GET','POST'])
@login_required
def account():
    form = updateAccountForm()
    users = User.query.all()
    posts = Post.query.filter_by(user_id=current_user.id)
    followers = []
    for user in users:
        if user.is_following(current_user):
            followers.append(user)
    postNum = posts.count()
    followerNum = current_user.followers.count()
    if form.validate_on_submit():
        if form.picture.data:
            proPicture = savingProPicture(form.picture.data)
            current_user.propic = proPicture
        current_user.username = form.username.data
        db.session.commit()
        flash('Account has been updated','success')
        return redirect(url_for('account'))
    elif request.method == 'GET':
        form.username.data = current_user.username
    image = url_for('static', filename='profilePics/' + current_user.propic)
    return render_template('account.html', image=image, form=form, users=users,postNum=postNum, followerNum=followerNum,followers=followers)

@app.route('/like/<int:id>', methods=['POST','GET'])
@login_required
def like(id):
    post = Post.query.filter_by(id=id)
    like = Like.query.filter_by(author=current_user,post_id=id).first()
    if not post:
        flash('Post does not exist', 'danger')
    elif like:
        db.session.delete(like)
        db.session.commit()

    else:
        like = Like(author=current_user,post_id=id)
        db.session.add(like)
        db.session.commit()
    
    return redirect(url_for('home'))


@app.route('/comment/<int:post_id>',methods=['GET','POST'])
@login_required
def create_comment(post_id):
    comment = request.form.get('text')
    if not comment:
        flash('Write a comment', 'danger')
    else:
        post = Post.query.filter_by(id=post_id)
        if post:
            final = Comment(text=comment, user_id=current_user.id, post_id=post_id)      
            db.session.add(final)
            db.session.commit()
        else:
            flash('Post not found', 'danger')
    return redirect(url_for('home'))

@app.route('/follow/<username>',methods=['POST','GET'])
@login_required
def follow(username):
    form = FollowForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=username).first()
        if user is None:
            flash('User not found')
            return redirect(url_for('home'))
        if user == current_user:
            flash('Cannot follow yourself')
            return redirect(url_for('profile',username=username))
        current_user.follow(user)
        db.session.commit()
        flash('You are following {}'.format(username))
        return redirect(url_for('home'))
    else:
        return redirect(url_for('home'))


@app.route('/unfollow/<username>', methods=['GET','POST'])
@login_required
def unfollow(username):
    form = FollowForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=username).first()
        if user is None:
            flash('User not found')
            return redirect(url_for('home'))
        if user == current_user:
            flash('You cannot unfollow yourself')
            return redirect(url_for('profile',username=username))
        current_user.unfollow(user)
        db.session.commit()
        flash("You've unfollowed {}".format(username))
        return redirect(url_for('profile',username=username))
    else:
        return redirect(url_for('home'))

@app.route('/delete-comment/<int:id>',methods=['POST','GET'])
@login_required
def delete_comment(id):
    tgtComment = Comment.query.filter_by(id=id).first()
    if not tgtComment:
        flash('Comment not found','danger')

    elif current_user != tgtComment.author and current_user != tgtComment.post.author:
        flash('You cannot delete this comment !')
    else:
        db.session.delete(tgtComment)
        db.session.commit()

    return redirect(url_for('home'))
    



@app.route("/post/<int:id>/delete",methods=['POST','GET'])
@login_required
def deletePost(id):
    post = Post.query.get_or_404(id)
    if post.author != current_user:
        abort(403)
    post_comments = Comment.query.filter_by(post_id=id)
    post_likes = Like.query.filter_by(post_id=id)
    if post_comments:
        for comment in post_comments:
            db.session.delete(comment)
    if post_likes:
        for like in post_likes:
            db.session.delete(like)
    db.session.delete(post)
    db.session.commit()
    flash('Your post has been deleted','success')
    return redirect(url_for('home'))


@app.route('/deleteUser/<int:id>', methods=['POST','GET'])
@login_required
def delete_user(id):
    user = User.query.get_or_404(id)
    if user != current_user:
        abort(403)
    user_posts = Post.query.filter_by(user_id=user.id)
    user_likes = Like.query.filter_by(user_id=user.id)
    user_comments = Comment.query.filter_by(user_id=user.id)
    if user_likes:
        for like in user_likes:
            db.session.delete(like)
    if user_comments:
        for comment in user_comments:
            db.session.delete(comment)

    if user_posts:
        for post in user_posts:
            db.session.delete(post)

    db.session.delete(user)
    db.session.commit()


    return redirect(url_for('login'))

    

    

